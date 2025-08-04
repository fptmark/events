import { Injectable } from '@angular/core';
import { FormGroup } from '@angular/forms';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { EntityService } from './entity.service';
import { MetadataService } from './metadata.service';
import { ViewMode, DETAILS } from './mode.service';
import currency from 'currency.js';

@Injectable({
  providedIn: 'root'
})
export class EntityFormService {

  constructor(
    private entityService: EntityService,
    private metadataService: MetadataService,
    private sanitizer: DomSanitizer
  ) {}

  // =====================================================
  // P1-P5 COMMON FUNCTIONS - UNIFIED ARCHITECTURE
  // =====================================================

  /**
   * P1: Populate enums - clear invalid values and set dropdown options
   * Used by: Create Mode, Edit Mode
   */
  populateEnums(entityType: string, entityForm: FormGroup, entity: any, sortedFields: string[]): void {
    for (const fieldName of sortedFields) {
      const fieldMeta = this.metadataService.getFieldMetadata(entityType, fieldName);
      const control = entityForm.get(fieldName);
      
      if (fieldMeta?.enum?.values && control && entity) {
        const rawValue = entity[fieldName];
        
        // Clear invalid enum values for optional fields
        if (rawValue && !fieldMeta.enum.values.includes(rawValue)) {
          console.log(`P1: Clearing invalid enum value "${rawValue}" for field ${fieldName}`);
          control.setValue(fieldMeta.required ? '' : null);
        }
      }
    }
  }

  /**
   * P2: Populate ObjectId selector (handled by component when selector is opened)
   * Used by: Create Mode, Edit Mode
   * Note: This is triggered on-demand when user clicks Select button
   */
  // Implementation is in component's showIdSelector() method

  /**
   * P3: Populate field errors below each field from payload
   * Used by: Edit Mode, Details Mode
   */
  populateFieldErrors(validationErrors: any[]): void {
    // Validation errors are stored in component and accessed by unified validation function
    // This function just ensures the errors are available for display
    console.log('P3: Field errors populated:', validationErrors.length);
  }

  /**
   * P4: Populate form fields from payload
   * Used by: Edit Mode, Details Mode
   */
  populateFormFields(entityType: string, entityForm: FormGroup, entity: any, sortedFields: string[], mode: ViewMode): void {
    if (!entityForm || !sortedFields.length || !entity) return;

    for (const fieldName of sortedFields) {
      const control = entityForm.get(fieldName);
      if (!control) continue;
      
      const metadata = this.metadataService.getFieldMetadata(entityType, fieldName);
      const rawValue = entity[fieldName];

      // Check if it's an ObjectId field with show configuration
      const showConfig = metadata?.ui?.show ? this.metadataService.getShowConfig(entityType, fieldName, mode) : null;

      // Force the type to text for id fields
      let type = (fieldName === 'id') ? 'text' : metadata?.type || 'text';
      
      if (type === 'ObjectId' && showConfig) {
        // For ObjectId fields with show config, use embedded FK data
        const formattedValue = this.entityService.formatObjectIdValueWithEmbeddedData(
          entityType, fieldName, mode, rawValue, entity, showConfig
        );
        control.setValue(formattedValue);
      } else {
        // For other field types, use the synchronous formatter
        const formattedValue = this.entityService.formatFieldValue(entityType, fieldName, mode, rawValue);
        control.setValue(formattedValue);
      }
    }
  }

  /**
   * P5: Unified validation for all modes
   * Used by: Create Mode, Edit Mode, Details Mode
   */
  performRealtimeValidation(entityType: string, fieldName: string, value: any, entity: any, mode: ViewMode, validationErrors?: any[]): string | null {
    // 1. CHECK SERVER VALIDATION ERRORS FIRST (from API responses)
    if (validationErrors && validationErrors.length > 0) {
      const serverError = validationErrors.find(error => error.field === fieldName);
      if (serverError) {
        return serverError.constraint;
      }
    }

    const fieldMeta = this.metadataService.getFieldMetadata(entityType, fieldName);
    if (!fieldMeta) return null;

    // 2. ENUM VALIDATION - check if CURRENT VALUE is in allowed enum values
    if (fieldMeta.enum?.values) {
      if (value && !fieldMeta.enum.values.includes(value)) {
        return `value "${value}" is not a valid selection`;
      }
    }

    // 3. OBJECTID VALIDATION - check if referenced entity exists (needs entity context for embedded data)
    if (fieldMeta.type === 'ObjectId' && entity && value) {
      const fkEntityName = fieldName.endsWith('Id') ? fieldName.slice(0, -2) : fieldName;
      const embeddedData = entity[fkEntityName];
      if (embeddedData?.exists === false) {
        // Use original entity value for stable error message
        const originalValue = entity[fieldName];
        return `Id ${originalValue} does not exist`;
      }
    }

    // 4. GENERAL FIELD VALIDATION - all other validation rules using CURRENT VALUE
    return this.getFieldValidationError(entityType, fieldName, value);
  }

  // =====================================================
  // VALIDATION METHODS
  // =====================================================

  /**
   * Check if a field value is invalid based on its metadata validation rules
   */
  isFieldValueInvalid(entityType: string, fieldName: string, value: any): boolean {
    const fieldMeta = this.metadataService.getFieldMetadata(entityType, fieldName);
    if (!fieldMeta) return false;

    // Check required fields
    if (fieldMeta.required && (value === null || value === undefined || value === '')) {
      return true;
    }

    // Skip validation if field is empty and not required
    if (!fieldMeta.required && (value === null || value === undefined || value === '')) {
      return false;
    }

    // Check enum values
    if (fieldMeta.enum?.values && value && !fieldMeta.enum.values.includes(value)) {
      return true;
    }

    // Check string validations
    if (typeof value === 'string') {
      // Min length
      if (fieldMeta.min_length && value.length < fieldMeta.min_length) {
        return true;
      }
      // Max length  
      if (fieldMeta.max_length && value.length > fieldMeta.max_length) {
        return true;
      }
      // Pattern validation
      if (fieldMeta.pattern?.regex) {
        const regex = new RegExp(fieldMeta.pattern.regex);
        if (!regex.test(value)) {
          return true;
        }
      }
    }

    // Check number validations
    if (typeof value === 'number') {
      // Min value
      if (fieldMeta.ge !== undefined && value < fieldMeta.ge) {
        return true;
      }
      // Max value
      if (fieldMeta.le !== undefined && value > fieldMeta.le) {
        return true;
      }
    }

    return false;
  }

  /**
   * Get validation error message for a field (excluding enums and ObjectIds)
   * Works across all modes - details, edit, create
   */
  getFieldValidationError(entityType: string, fieldName: string, value: any): string | null {
    const fieldMeta = this.metadataService.getFieldMetadata(entityType, fieldName);
    if (!fieldMeta) return null;

    // Skip enums and ObjectIds - they have their own error handling
    if (fieldMeta.enum?.values || fieldMeta.type === 'ObjectId') {
      return null;
    }

    // Check required fields
    if (fieldMeta.required && (value === null || value === undefined || value === '')) {
      return `${this.getFieldDisplayName(entityType, fieldName)} is required.`;
    }

    // Skip validation if field is empty and not required
    if (!fieldMeta.required && (value === null || value === undefined || value === '')) {
      return null;
    }

    // Check string validations
    if (typeof value === 'string') {
      // Min length
      if (fieldMeta.min_length && value.length < fieldMeta.min_length) {
        return `${this.getFieldDisplayName(entityType, fieldName)} must be at least ${fieldMeta.min_length} characters.`;
      }
      // Max length  
      if (fieldMeta.max_length && value.length > fieldMeta.max_length) {
        return `${this.getFieldDisplayName(entityType, fieldName)} cannot exceed ${fieldMeta.max_length} characters.`;
      }
      // Pattern validation
      if (fieldMeta.pattern?.regex) {
        const regex = new RegExp(fieldMeta.pattern.regex);
        if (!regex.test(value)) {
          return fieldMeta.pattern.message || `${this.getFieldDisplayName(entityType, fieldName)} has an invalid format.`;
        }
      }
    }

    // Check number validations
    if (typeof value === 'number') {
      // Min value
      if (fieldMeta.ge !== undefined && value < fieldMeta.ge) {
        return `${this.getFieldDisplayName(entityType, fieldName)} must be at least ${fieldMeta.ge}.`;
      }
      // Max value
      if (fieldMeta.le !== undefined && value > fieldMeta.le) {
        return `${this.getFieldDisplayName(entityType, fieldName)} cannot exceed ${fieldMeta.le}.`;
      }
    }

    return null;
  }

  /**
   * Get field display name for error messages
   */
  private getFieldDisplayName(entityType: string, fieldName: string): string {
    const fieldMeta = this.metadataService.getFieldMetadata(entityType, fieldName);
    return fieldMeta?.ui?.displayName || fieldName;
  }

  /**
   * Get display value without warnings - just clean display text
   */
  getDisplayValue(
    entityType: string, 
    fieldName: string, 
    entityForm: FormGroup, 
    entity: any
  ): SafeHtml {
    const controlValue = entityForm.get(fieldName)?.value;
    
    // Handle empty values with proper spacing
    const displayText = controlValue || (controlValue === 0 ? '0' : '&nbsp;');
    
    return this.sanitizer.bypassSecurityTrustHtml(displayText);
  }

}