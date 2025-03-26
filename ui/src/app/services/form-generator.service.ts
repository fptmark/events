import { Injectable } from '@angular/core';
import { FormBuilder, FormGroup, Validators, AbstractControl, ValidationErrors } from '@angular/forms';
import { EntityMetadata } from './entity.service';
import { EntityDisplayService } from './entity-display.service';

@Injectable({
  providedIn: 'root'
})
export class FormGeneratorService {

  constructor(
    private fb: FormBuilder,
    private entityDisplay: EntityDisplayService
  ) {}

  generateForm(metadata: EntityMetadata, initialData?: any): FormGroup {
    const formGroup: { [key: string]: AbstractControl } = {};
    const fields = metadata.fields;
    
    // Process all fields from metadata
    Object.keys(fields).forEach(fieldName => {
      const fieldMeta = fields[fieldName];
      if (!fieldMeta) return;
      
      // No field skipping based on field names
      
      // Skip readonly fields for new entities
      if (!initialData && fieldMeta.readOnly) return;
      
      // Use showInView to determine field visibility
      if (!initialData) {
        // For new entities, only include fields for forms
        if (!this.entityDisplay.showInView(fieldMeta, 'form')) {
          return;
        }
      } else {
        // For existing entities (edit mode)
        // Include fields marked for forms or details (to show readonly fields)
        if (!this.entityDisplay.showInView(fieldMeta, 'form') && 
            !this.entityDisplay.showInView(fieldMeta, 'details')) {
          return;
        }
      }
      
      const validators = this.getValidators(fieldMeta);
      
      const initialValue = initialData && initialData[fieldName] !== undefined 
        ? initialData[fieldName] 
        : this.getDefaultValue(fieldMeta);
      
      // For readOnly fields in edit mode, create a disabled control
      if (fieldMeta.readOnly && initialData) {
        formGroup[fieldName] = this.fb.control({
          value: initialValue, 
          disabled: true
        }, validators);
      } else {
        formGroup[fieldName] = this.fb.control(initialValue, validators);
      }
    });
    
    return this.fb.group(formGroup);
  }
  
  private getValidators(fieldMeta: any): any[] {
    const validators = [];
    
    if (fieldMeta.required) {
      validators.push(Validators.required);
    }
    
    if (fieldMeta.minLength) {
      validators.push(Validators.minLength(fieldMeta.minLength));
    }
    
    if (fieldMeta.maxLength) {
      validators.push(Validators.maxLength(fieldMeta.maxLength));
    }
    
    if (fieldMeta.pattern) {
      validators.push(Validators.pattern(fieldMeta.pattern));
    }
    
    if (fieldMeta.min !== undefined) {
      validators.push(Validators.min(fieldMeta.min));
    }
    
    if (fieldMeta.max !== undefined) {
      validators.push(Validators.max(fieldMeta.max));
    }
    
    // Special case handling for email fields
    if (fieldMeta.type === 'String' && 
        (fieldMeta.widget === 'email' || fieldMeta.pattern?.includes('@'))) {
      validators.push(Validators.email);
    }
    
    return validators;
  }
  
  private getDefaultValue(fieldMeta: any): any {
    switch (fieldMeta.type) {
      case 'String':
        // For select fields with options, default to first option if required
        if (fieldMeta.widget === 'select' && fieldMeta.options?.length > 0 && fieldMeta.required) {
          return fieldMeta.options[0];
        }
        return '';
      case 'Number':
      case 'Integer':
        return fieldMeta.required ? 0 : null;
      case 'Boolean':
        return false;
      case 'Array':
        return [];
      case 'JSON':
        return {};
      case 'ISODate':
        return null;
      case 'ObjectId':
        return '';
      default:
        return null;
    }
  }
  
  getFormSortedFields(metadata: EntityMetadata): string[] {
    const fields = metadata.fields;
    const fieldNames = Object.keys(fields);
    
    // Filter fields based on display property and field metadata
    const filteredFields = fieldNames.filter(name => {
      const fieldMeta = fields[name];
      if (!fieldMeta) return false;
      
      // Skip readOnly fields for create forms
      if (fieldMeta.readOnly) return false;
      
      // Check if field should be shown in forms
      return this.entityDisplay.showInView(fieldMeta, 'form');
    });
    
    // Return filtered fields directly without sorting
    return filteredFields;
  }
}