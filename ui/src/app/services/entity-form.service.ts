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

  // =====================================================
  // FORM POPULATION METHODS
  // =====================================================

  /**
   * Populates form values based on mode and entity data
   */
  populateFormValues(
    entityType: string,
    mode: ViewMode,
    entityForm: FormGroup,
    sortedFields: string[],
    entityData?: any
  ): void {
    if (!entityForm || !sortedFields.length) return;

    for (const fieldName of sortedFields) {
      const control = entityForm.get(fieldName);
      if (!control) continue;
      
      // Get field metadata
      const metadata = this.metadataService.getFieldMetadata(entityType, fieldName);
      const rawValue = entityData?.[fieldName];

      // For enum fields in edit mode, clear invalid values to null for optional fields
      if (mode !== DETAILS && metadata?.enum?.values && rawValue && !metadata.enum.values.includes(rawValue)) {
        console.log(`Clearing invalid enum value "${rawValue}" for field ${fieldName}`);
        control.setValue(metadata.required ? '' : null);
        continue;
      }

      // Check if it's an ObjectId field with a show configuration for the current mode
      const showConfig = metadata?.ui?.show ? this.metadataService.getShowConfig(entityType, fieldName, mode) : null;

      // force the type to text for id fields
      let type = (fieldName === 'id') ? 'text' : metadata?.type || 'text'
      console.log(`Processing field ${fieldName} of type ${type} with raw value:`, rawValue);
      
      if (type === 'ObjectId' && showConfig) {
        // For ObjectId fields with show config, use embedded FK data
        const formattedValue = this.entityService.formatObjectIdValueWithEmbeddedData(
          entityType, fieldName, mode, rawValue, entityData, showConfig
        );
        
        // If it's in details mode, sanitize the HTML output
        if (mode === DETAILS) {
          control.setValue(this.sanitizer.bypassSecurityTrustHtml(formattedValue));
        } else {
          control.setValue(formattedValue);
        }
      } else {
        // For other field types or ObjectId without show config, use the synchronous formatter
        console.log(`Formatting field ${fieldName} with raw value:`, rawValue);
        const formattedValue = this.entityService.formatFieldValue(entityType, fieldName, mode, rawValue);
        
        // If it's an ObjectId field in details mode (without show config), sanitize the HTML
        if (type === 'ObjectId' && mode === DETAILS) {
           control.setValue(this.sanitizer.bypassSecurityTrustHtml(formattedValue));
        } else {
          control.setValue(formattedValue);
        }
      }
    }
  }

  // =====================================================
  // FORM PROCESSING METHODS
  // =====================================================

  /**
   * Process form data before submitting to the API
   */
  processFormData(
    entityType: string,
    entityForm: FormGroup,
    getFieldDisplayName: (fieldName: string) => string,
    notificationService: any
  ): Record<string, any> {
    const processedData: Record<string, any> = {};

    try {
      if (!entityForm) return processedData;

      // Process all form controls directly (including disabled fields)
      for (const fieldName in entityForm.controls) {
        const control = entityForm.controls[fieldName];
        const fieldMeta = this.metadataService.getFieldMetadata(entityType, fieldName);
        const value = control.value;

        // Special handling for boolean fields - always include in payload
        if (fieldMeta?.type === 'Boolean') {
          processedData[fieldName] = value === null || value === undefined ? false : Boolean(value);
          continue;
        }
        
        const isEmpty = value === undefined || value === null || (typeof value === 'string' && value.trim() === '');
        if (isEmpty && !fieldMeta?.required) {
          continue;
        }

        // Special handling for Currency fields
        if (fieldMeta?.type === 'Currency') {
          if (typeof value === 'string' && value.trim() !== '') {
            try {
              // Validate that only legal currency characters are present
              const legalCurrencyPattern = /^[\$\-\(\)\,\.0-9\s]+$/;
              if (!legalCurrencyPattern.test(value)) {
                throw new Error('Invalid characters in currency value. Only [$-().,] and numbers are allowed.');
              }
              
              const parsed = currency(value, {
                precision: 2, 
                symbol: '$',
                decimal: '.',
                separator: ',',
                errorOnInvalid: true
              });
              
              processedData[fieldName] = parsed.value;
              continue;
            } catch (e) {
              // If parsing fails, mark the field as invalid
              console.error('Currency parsing error:', e);
              control.setErrors({ 'currencyFormat': 'Invalid currency format. Use $X,XXX.XX or (X,XXX.XX) for negative values.' });
              
              // Show error notification
              notificationService.showError({
                message: `Invalid currency format in ${getFieldDisplayName(fieldName)}`,
                error_type: 'validation_error',
                context: {
                  entity: entityType,
                  invalid_fields: [{
                    field: fieldName,
                    constraint: 'Invalid currency format. Use $X,XXX.XX or (X,XXX.XX) for negative values.'
                  }]
                }
              });
              
              // Set this flag to make the error visible
              control.markAsTouched();
              control.markAsDirty();
              continue;
            }
          }
        }

        // Special handling for Date and Datetime fields
        if (fieldMeta?.type === 'Date' || fieldMeta?.type === 'Datetime') {
          if (typeof value === 'string' && value.trim() !== '') {
            try {
                const dateValue = new Date(value);
                if (!isNaN(dateValue.getTime())) {
                  const isoValue = dateValue.toISOString();
                  processedData[fieldName] = fieldMeta?.type === 'Date' ? isoValue.split('T')[0] : isoValue
                  continue;
                }
            } catch (e) {
              console.error('Date/Datetime parsing error:', e);
              // Let it fall through to regular processing
            }
          }
        }

        // For all other field types
        // Special handling: skip empty enum fields entirely (even if required)
        if (fieldMeta?.enum?.values && isEmpty) {
          continue;
        }
        
        // Include field if it's auto-generated/updated, required, or has a value
        if (fieldMeta?.autoUpdate || fieldMeta?.autoGenerate || fieldMeta?.required || !isEmpty) {
            processedData[fieldName] = isEmpty ? null : value;
        }
      }
    } catch (error) {
      console.error('Error processing form data:', error);
    }

    return processedData;
  }
}