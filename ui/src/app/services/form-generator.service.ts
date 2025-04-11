import { Injectable } from '@angular/core';
import { FormBuilder, FormGroup, Validators, AbstractControl, ValidationErrors } from '@angular/forms';
import { FieldMetadata, MetadataService } from './metadata.service';
import { EntityService } from './entity.service';

export const VIEW = 'View';
export const CREATE  = 'Create';
export const EDIT  = 'Edit';
export type FormMode = typeof VIEW | typeof CREATE | typeof EDIT
@Injectable({
  providedIn: 'root'
})

export class FormGeneratorService {

  constructor(
    private fb: FormBuilder,
    private entityService: EntityService,
    private metadataService: MetadataService
  ) {}

  /**
   * Generate a complete entity form with both the form controls and display fields
   * @param entityType The type of entity to create a form for
   * @param mode The mode of the form: 'create', 'edit', or 'view'
   * @param entityData Optional entity data for edit mode
   * @returns An object with the form and ordered display fields
   * 
   * This handles create, edit and view modes.
   */
  generateEntityForm(entityType: string, mode: FormMode): { form: FormGroup, displayFields: string[] } {
    const formGroup: { [key: string]: AbstractControl } = {};
    const idField = '_id'
    
    // Get fields to display from entity service
    let viewFields: string[] = this.entityService.getViewFields(entityType, 'form');
    let displayFields: string[] // may add or delete the id field later

    // Manage ID field - it should be first in edit and view modes and removed in create mode
    displayFields = viewFields.filter(fieldName => fieldName !== idField);
    if (mode === VIEW || mode === EDIT) { // Make sure the id field is first
      displayFields.unshift(idField);
    }

    // Process all fields to create form controls
    displayFields.forEach(fieldName => {
      let validators: any[] = [];
      
      try {
        // Determine if field should be disabled by non-data-dependent rules
        let isDisabled = mode === VIEW; // All fields disabled in view mode
        
        // ID fields are always disabled
        if (fieldName === idField) {
          isDisabled = true;
        }
        
        // Get field validators and metadata
        const fieldMeta = this.metadataService.getFieldMetadata(entityType, fieldName);
        
        // Add validators if not in view mode and field has metadata
        if (fieldMeta && mode !== VIEW) {
          validators = this.getValidators(fieldMeta);
          
          // Field marked read-only in metadata
          if (fieldMeta.ui?.readOnly) {
            isDisabled = true;
          }
          
          // Auto-generate/update ISODate fields should be disabled in all modes
          if (fieldMeta.type === 'ISODate' && (fieldMeta.autoGenerate || fieldMeta.autoUpdate)) {
            isDisabled = true;
          }
        }
        
        // Create the form control with appropriate disabled state
        let ctl = this.fb.control({
          // No initial value - will be set by entity-form
        }, validators);
        if (isDisabled) {
          ctl.disable();
        }
        formGroup[fieldName] = ctl
      } catch (error) {
        console.error(`Error processing field ${fieldName}:`, error);
      } 
    })

    return {
      form: this.fb.group(formGroup),
      displayFields: displayFields
    };
  }
  
  // Old method removed - we only need generateEntityForm
  
  private getValidators(fieldMeta: any): any[] {
    const validators = [];
    
    // Required is at the root level according to sample payload
    if (fieldMeta.required) {
      validators.push(Validators.required);
    }
    
    // These validations might be in the UI object or at root level
    const minLength = fieldMeta.ui?.minLength || fieldMeta.minLength;
    if (minLength) {
      validators.push(Validators.minLength(minLength));
    }
    
    const maxLength = fieldMeta.ui?.maxLength || fieldMeta.maxLength;
    if (maxLength) {
      validators.push(Validators.maxLength(maxLength));
    }
    
    const pattern = fieldMeta.ui?.pattern || fieldMeta.pattern;
    if (pattern) {
      validators.push(Validators.pattern(pattern));
    }
    
    const min = fieldMeta.ui?.min !== undefined ? fieldMeta.ui.min : fieldMeta.min;
    if (min !== undefined) {
      validators.push(Validators.min(min));
    }
    
    const max = fieldMeta.ui?.max !== undefined ? fieldMeta.ui.max : fieldMeta.max;
    if (max !== undefined) {
      validators.push(Validators.max(max));
    }
    
    // Special case handling for email fields
    const type = fieldMeta.type;
    const widget = fieldMeta.ui?.widget || fieldMeta.widget;
    
    if (type === 'String' && (widget === 'email' || pattern?.includes('@'))) {
      validators.push(Validators.email);
    }
    
    return validators;
  }
  
  /**
   * Get the appropriate widget type for a field based on its metadata and mode
   * @param entityType The type of entity
   * @param fieldName The name of the field
   * @param mode The form mode (view/edit/create)
   * @returns The widget type to use
   */
  getFieldWidget(entityType: string, fieldName: string, mode: FormMode): string {
    // For view mode, always use text inputs to avoid browser-specific rendering issues
    if (mode === VIEW) {
      return 'text';
    }
    
    if (fieldName === '_id') return 'text';
    
    const fieldMeta = this.metadataService.getFieldMetadata(entityType, fieldName);
    if (!fieldMeta) return 'text';
    
    // If widget is explicitly specified in ui object, use it
    if (fieldMeta.ui?.widget) return fieldMeta.ui.widget;
    
    // Check if field has enum values - use select dropdown
    if (fieldMeta.enum && fieldMeta.enum.values && fieldMeta.enum.values.length > 0) {
      return 'select';
    }
    
    // Default widgets based on field type
    const fieldType = fieldMeta.type;
    switch (fieldType) {
      case 'Boolean':
        return 'checkbox';
      case 'ISODate':
        // For auto fields always use text to avoid browser issues
        if (fieldMeta.autoGenerate || fieldMeta.autoUpdate) {
          return 'text';
        }
        return 'date';
      case 'String':
        // Special string field types based on metadata patterns, not field names
        if (fieldMeta.pattern?.regex?.includes('@')) return 'email';
        if (fieldMeta.maxLength && fieldMeta.maxLength > 100) return 'textarea';
        return 'text';
      case 'ObjectId':
        return 'reference';
      case 'Array':
      case 'Array[String]':
        return 'array';
      case 'JSON':
        return 'json';
      default:
        return 'text';
    }
  }
} 