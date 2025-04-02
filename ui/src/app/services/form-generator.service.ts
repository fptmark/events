import { Injectable } from '@angular/core';
import { FormBuilder, FormGroup, Validators, AbstractControl, ValidationErrors } from '@angular/forms';
import { Entity } from './entity.service';
import { AllEntitiesService, AllEntitiesMetadata } from './all-entities.service';

@Injectable({
  providedIn: 'root'
})
export class FormGeneratorService {

  constructor(
    private fb: FormBuilder,
    private allEntitiesService: AllEntitiesService
  ) {}

  generateForm(metadata: AllEntitiesMetadata, entity?: Entity): FormGroup {
    const formGroup: { [key: string]: AbstractControl } = {};
    
    // If this is an edit operation and we have an entity
    if (entity) {
      // Use the entity object's properties to build form fields
      Object.keys(entity).forEach(fieldName => {
        // Skip internal fields like _id for create forms if no entity is provided
        if (fieldName === '_id' || fieldName === 'createdAt' || fieldName === 'updatedAt') {
          // For _id and timestamp fields, create disabled controls
          formGroup[fieldName] = this.fb.control({
            value: entity[fieldName],
            disabled: true
          });
          return;
        }
        
        // Get field metadata if available
        const fieldMeta = metadata.fields?.[fieldName];
        const validators = fieldMeta ? this.getValidators(fieldMeta) : [];
        
        // Check if field should be read-only
        const isReadOnly = fieldMeta?.ui?.readOnly === true;
        
        if (isReadOnly) {
          // Create disabled control for read-only fields
          formGroup[fieldName] = this.fb.control({
            value: entity[fieldName], 
            disabled: true
          }, validators);
        } else {
          // Create normal control
          formGroup[fieldName] = this.fb.control(entity[fieldName], validators);
        }
      });
    } else {
      // This is a create operation
      // Use metadata fields to build the form
      if (metadata.fields) {
        Object.keys(metadata.fields).forEach(fieldName => {
          const fieldMeta = metadata.fields[fieldName];
          
          // Skip read-only fields for create forms
          if (fieldMeta?.ui?.readOnly) return;
          
          // Skip fields that aren't meant for forms
          if (fieldMeta?.displayPages && 
              fieldMeta.displayPages !== 'all' && 
              !fieldMeta.displayPages.includes('form')) {
            return;
          }
          
          const validators = this.getValidators(fieldMeta);
          const defaultValue = this.getDefaultValue(fieldMeta);
          
          formGroup[fieldName] = this.fb.control(defaultValue, validators);
        });
      }
    }
    
    return this.fb.group(formGroup);
  }
  
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
  
  private getDefaultValue(fieldMeta: any): any {
    const type = fieldMeta.type;
    const widget = fieldMeta.ui?.widget || fieldMeta.widget;
    const enumValues = fieldMeta.enum?.values;
    const required = fieldMeta.required;
    
    switch (type) {
      case 'String':
        // For select fields with enum values, default to first value if required
        if (widget === 'select' && enumValues?.length > 0 && required) {
          return enumValues[0];
        }
        return '';
      case 'Number':
      case 'Integer':
        return required ? 0 : null;
      case 'Boolean':
        return false;
      case 'Array':
      case 'Array[String]':
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
  
  getFormSortedFields(metadata: AllEntitiesMetadata): string[] {
    if (!metadata.fields) return [];
    
    const fieldNames = Object.keys(metadata.fields);
    
    // Filter fields based on display property and field metadata
    const filteredFields = fieldNames.filter(name => {
      const fieldMeta = metadata.fields?.[name];
      if (!fieldMeta) return false;
      
      // Skip readOnly fields for create forms
      if (fieldMeta.ui?.readOnly) return false;
      
      // Check if field should be shown in forms based on displayPages
      const displayPages = fieldMeta.displayPages || '';
      return displayPages === '' || 
             displayPages === 'all' || 
             displayPages.includes('form');
    });
    
    // Return filtered fields directly without sorting
    return filteredFields;
  }
}