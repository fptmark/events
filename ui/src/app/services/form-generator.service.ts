import { Injectable } from '@angular/core';
import * as currencyLib from 'currency.js';
import { FormBuilder, FormGroup, Validators, AbstractControl, ValidationErrors } from '@angular/forms';
import { FieldMetadata, MetadataService } from './metadata.service';
import { EntityService } from './entity.service';
import { ViewService, ViewMode, VIEW, EDIT, CREATE } from './view.service';
import { Constants } from '../constants'; // Assuming idField is defined in constants.ts

// No need for constants or FormMode type anymore
@Injectable({
  providedIn: 'root'
})

export class FormGeneratorService {

  constructor(
    private fb: FormBuilder,
    private entityService: EntityService,
    private metadataService: MetadataService,
    private viewService: ViewService
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
  generateEntityForm(entityType: string, mode: ViewMode): { form: FormGroup, displayFields: string[] } {
    const formGroup: { [key: string]: AbstractControl } = {};
    
    // Get fields to display from entity service
    let viewFields: string[] = this.entityService.getViewFields(entityType, mode)
    let displayFields: string[] // may add or delete the id field later

    // Manage ID field - it should be first in edit and view modes and removed in create mode
    displayFields = viewFields.filter(fieldName => fieldName !== Constants.idField);
    if (this.viewService.inViewMode(mode) || this.viewService.inEditMode(mode)) { // Make sure the id field is first
      displayFields.unshift(Constants.idField);
    }

    // Process all fields to create form controls
    displayFields.forEach(fieldName => {
      let validators: any[] = [];
      
      try {
        // Get field validators and metadata
        const fieldMeta = this.metadataService.getFieldMetadata(entityType, fieldName);
        
        // Add validators if not in view mode and field has metadata
        if (fieldMeta && !this.viewService.inViewMode(mode)) {
          validators = this.getValidators(fieldMeta);
        }

        // Create the form control with appropriate disabled state
        let ctl = this.fb.control({
          // No initial value - will be set by entity-form
        }, validators);
        if (this.getFieldAttributes(entityType, fieldName, mode).enabled === false) {
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
  
  private getValidators(fieldMeta: FieldMetadata): any[] {
    const validators = [];

    // Required is at the root level according to sample payload
    // Never add required validator for Boolean fields regardless of required flag
    // This is because Booleans always have a value (true/false)
    if (fieldMeta.required && fieldMeta.type !== 'Boolean') {
      validators.push(Validators.required);
    }

    // These validations might be in the UI object or at root level
    const minLength = fieldMeta.min_length;
    if (minLength) {
      validators.push(Validators.minLength(minLength));
    }

    const maxLength = fieldMeta.max_length;
    if (maxLength) {
      validators.push(Validators.maxLength(maxLength));
    }

    const pattern = fieldMeta.pattern;
    if (pattern && pattern.regex) {
      validators.push(Validators.pattern(pattern.regex));
    }

    const min = fieldMeta?.ge
    if (min !== undefined) {
      validators.push(Validators.min(min));
    }

    const max = fieldMeta?.le
    if (max !== undefined) {
      validators.push(Validators.max(max));
    }

    // Special case handling for specific field types
    const type = fieldMeta.type;

    if (pattern?.regex?.includes('@')) {
      validators.push(Validators.email);
    }

    // Currency type validation
    if (type === 'Currency') {
      validators.push(this.currencyValidator);
    }

    return validators;
  }

  private currencyValidator(control: AbstractControl): ValidationErrors | null {
    const value = control.value;
    
    // Skip validation if empty for optional fields
    if ((value === null || value === undefined || value === '' || 
         (typeof value === 'string' && value.trim() === '')) && 
        !control.hasValidator(Validators.required)) {
      return null;
    }
    
    // Required validation only - anything non-empty passes
    if (control.hasValidator(Validators.required) && 
        (value === null || value === undefined || value === '' || 
         (typeof value === 'string' && value.trim() === ''))) {
      return { 'required': true };
    }
    
    // No real-time validation - allow any input
    return null;
  }
  
  /**
   * Get the appropriate input control type for a field based on its metadata and mode
   * @param entityType The type of entity
   * @param fieldName The name of the field
   * @param mode The form mode (view/edit/create)
   * @returns The input control type to use
   */
  getFieldAttributes(entityType: string, fieldName: string, mode: ViewMode): { fieldType: string, enabled: boolean } {
    // _id field is always a text field
    if (fieldName === Constants.idField) return {fieldType: 'text', enabled: false};
    
    const fieldMeta = this.metadataService.getFieldMetadata(entityType, fieldName);
    if (!fieldMeta) return {fieldType: 'text', enabled: true};
    
    // Always return ObjectId for both view and edit modes
    if (fieldMeta.type === "ObjectId") {
      return {fieldType: 'ObjectId', enabled: true}; // clickable in all modes
    }

    // For view mode, use appropriate read-only controls
    if (this.viewService.inViewMode(mode)) {
      // Special case for Boolean fields - use checkbox even in view mode
      if (fieldMeta.type === 'Boolean') {
        return { fieldType: 'checkbox', enabled: false };
      }
      // For other fields, use text inputs in view mode
      return { fieldType: 'text', enabled: false };
    } else {    // Create and edit modes
    
      // Usually for ISODate fields but perhaps others?
      if (fieldMeta.autoGenerate || fieldMeta.autoUpdate) {
        const enabled = fieldMeta?.ui?.clientEdit ?? false;  // client_edit allows the client to edit an auto field
        return { fieldType: 'text', enabled: enabled };
      }

      // Check if field has enum values - use select dropdown
      if (fieldMeta.enum && fieldMeta.enum.values && fieldMeta.enum.values.length > 0) {
        return { fieldType: 'select', enabled: true };
      }
    
      // Default input control types based on field type
      let fieldType = fieldMeta.type;
      switch (fieldType) {
        case 'Boolean':
          fieldType = 'checkbox'; break;
        case 'ISODate':
          fieldType = 'date'; break;
        case 'String':
          fieldType =  ((fieldMeta?.max_length ?? 0) > 100) ? 'textarea': 'text'
          break
        case 'ObjectId':
          fieldType = 'ObjectId'; break
        case 'Array':
        case 'Array[String]': 
          fieldType = 'array';
          break;
        case 'JSON': 
          fieldType = 'json';
          break;
        case 'Integer':
        case 'Number':
        case 'Float':
          fieldType = 'number';
          break;
        default:
          fieldType = 'text';
      }
      return { fieldType: fieldType, enabled: true };
    }
  }
} 