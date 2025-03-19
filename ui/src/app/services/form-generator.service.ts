import { Injectable } from '@angular/core';
import { FormBuilder, FormGroup, Validators, AbstractControl, ValidationErrors } from '@angular/forms';
import { EntityMetadata } from './entity.service';

@Injectable({
  providedIn: 'root'
})
export class FormGeneratorService {

  constructor(private fb: FormBuilder) {}

  generateForm(metadata: EntityMetadata, initialData?: any): FormGroup {
    const formGroup: { [key: string]: AbstractControl } = {};
    const fields = metadata.fields;
    
    // Skip BaseEntity fields for creating new entities
    const skipFields = ['_id', 'createdAt', 'updatedAt'];
    
    Object.keys(fields).forEach(fieldName => {
      if (skipFields.includes(fieldName)) {
        return;
      }
      
      const fieldMeta = fields[fieldName];
      const validators = this.getValidators(fieldMeta);
      
      const initialValue = initialData && initialData[fieldName] !== undefined 
        ? initialData[fieldName] 
        : this.getDefaultValue(fieldMeta);
        
      formGroup[fieldName] = this.fb.control(initialValue, validators);
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
    
    // Remove BaseEntity fields
    const filteredFields = fieldNames.filter(name => 
      !['_id', 'createdAt', 'updatedAt'].includes(name)
    );
    
    // Create a map of displayAfterField values to field names
    const displayAfterMap = new Map<string, string[]>();
    
    filteredFields.forEach(fieldName => {
      const displayAfter = fields[fieldName].displayAfterField || '';
      if (!displayAfterMap.has(displayAfter)) {
        displayAfterMap.set(displayAfter, []);
      }
      displayAfterMap.get(displayAfter)!.push(fieldName);
    });
    
    // Build the sorted field list
    const sortedFields: string[] = [];
    let current = '';
    
    while (sortedFields.length < filteredFields.length) {
      const fieldsAfterCurrent = displayAfterMap.get(current) || [];
      
      if (fieldsAfterCurrent.length === 0) {
        // Find any remaining fields and add them
        for (const fieldName of filteredFields) {
          if (!sortedFields.includes(fieldName)) {
            sortedFields.push(fieldName);
          }
        }
        break;
      }
      
      fieldsAfterCurrent.forEach(fieldName => {
        if (!sortedFields.includes(fieldName)) {
          sortedFields.push(fieldName);
          current = fieldName;
        }
      });
    }
    
    return sortedFields;
  }
}