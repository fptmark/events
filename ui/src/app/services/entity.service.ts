import { Injectable } from '@angular/core';
import { MetadataService, FieldMetadata } from './metadata.service';
import { ViewService, ViewMode, VIEW, EDIT, CREATE } from './view.service';
import { FieldOrderService } from './field-order.service';
import { NavigationService } from './navigation.service';
import { Router } from '@angular/router';

export interface EntityResponse<> {
  data: [];
  // No metadata in entity responses anymore, it comes from all-entities
}

@Injectable({
  providedIn: 'root'
})
export class EntityService {
  constructor(
    private fieldOrderService: FieldOrderService,
    private metadataService: MetadataService,
    private router: Router,
    private viewService: ViewService,
    private navigationService: NavigationService
  ) {}

   // view can be 'details', 'summary' and/or 'form' e.g. 'details|summary'
   getViewFields(entityName: string, currentView: string): string[] {
    const metadata = this.metadataService.getEntityMetadata(entityName)
    const allFields = ['_id', ...Object.keys(metadata.fields)];

    const visibleFields = allFields.filter(field => {
      const fieldMetadata = metadata.fields[field]
      // Skip hidden fields
      if (fieldMetadata?.ui?.display === 'hidden') {
        return false
      }
      
      // Use ViewService to determine if field is visible in current view/mode
      const displayPages = fieldMetadata?.ui?.displayPages ?? ''
      return this.viewService.existsInMode(displayPages, currentView);
    })
    return this.fieldOrderService.orderFields(visibleFields, metadata);
  }


  getFieldDisplayName(entityName: string, fieldName: string): string {
    try {
      const metadata = this.metadataService.getEntityMetadata(entityName);
      return metadata.fields[fieldName]?.ui?.displayName || fieldName;
    } catch (error) {
      return fieldName;
    }
  }

  formatFieldValue(entityType: string, fieldName: string, mode: ViewMode, value: any): string {
    if (!value || value === undefined || value === null) {
      return '';
    }

    let metadata = this.metadataService.getFieldMetadata(entityType, fieldName)
    let type = metadata?.type || 'text'
    let format = metadata?.ui?.format 

    // format Foreign keys and date for non-create modes
    if (this.viewService.inSummaryMode(mode) && metadata?.type === 'ObjectId') {
      let entity = fieldName.substring(0, fieldName.length - 2) // Remove 'Id' suffix
      let link = `entity/${entity}/${value}`
      return `<a href=${link}>View</a>`
    }

    // Date field handling
    if (type === 'ISODate') {
      
      // For edit mode, use current date for auto-update fields
      if (this.viewService.inEditMode(mode)) {
        if (metadata?.autoUpdate) {
          value = new Date().toISOString().slice(0, 10); // Format for date (YYYY-MM-DD)
        }
      }
      
      // For create mode, use current date for auto-generate/update fields
      if (this.viewService.inCreateMode(mode)) {
        if (metadata?.autoGenerate || metadata?.autoUpdate) {
          value = new Date().toISOString().slice(0, 10); // Format for date (YYYY-MM-DD)
        }
      }
      
      if (this.viewService.inCreateMode(mode)) {
        return this.getDefaultValue(metadata);
      }

      return this.formatDate(value, mode)
    }

    // Boolean handling
    if (typeof value === 'boolean') {
      return value ? 'Yes' : 'No';
    } else if (metadata?.type === 'Boolean' && typeof value === 'string') {
      return value.toLowerCase() === 'true' ? 'Yes' : 'No';
    }
    
    // Object handling
    if (typeof value === 'object' && value !== null) {
      return JSON.stringify(value);
    }
    
    // Default string conversion
    return String(value);
  }

  formatDate(value: string, mode?: ViewMode): string {
    try {
      const date = new Date(value);
      
      // When in an edit-capable form, we need the date in YYYY-MM-DD format for HTML date input
      if (mode && (mode === EDIT || mode === CREATE)) {
        // Format as YYYY-MM-DD for HTML date input - simpler approach using ISO string
        return date.toISOString().slice(0, 10);
      }
      
      // For display-only mode, use localized date format
      return date.toLocaleDateString();
    }
    catch (e) {
      return value;
    }
  }

  canRead(entityType: string): boolean {
    return this.metadataService.isValidOperation(entityType, 'r');
  }

  canUpdate(entityType: string): boolean {
    return this.metadataService.isValidOperation(entityType, 'u');
  }

  canDelete(entityType: string): boolean {
    return this.metadataService.isValidOperation(entityType, 'd');
  }

  // Custom actions are not currently implemented in the stateless approach
  // getCustomActions(entity: Entity): { key: string, label: string, icon?: string }[] {
  //   // Will be implemented when hooks are added back
  //   return [];
  // }
  
  // executeCustomAction(actionKey: string, entity: Entity): void {
  //   // Will be implemented when hooks are added back
  //   console.log(`Custom action ${actionKey} would be executed on entity:`, entity);
  // }

  navigateToCreate(entityType: string): void {
    // Navigate to create page for this entity type
    this.router.navigate(['/entity', entityType, 'create']);
  }

  viewEntity(entityType: string, id: string): void {
    // Navigate to detail view for specific entity
    this.router.navigate(['/entity', entityType, id]);
  }

  editEntity(entityType: string, id: string): void {
    // Navigate to edit page for specific entity
    this.router.navigate(['/entity', entityType, id, 'edit']);
  }

  private getDefaultValue(fieldMeta: any): any {
    const type = fieldMeta.type;
    const enumValues = fieldMeta.enum?.values;
    const required = fieldMeta.required;
    
    switch (type) {
      case 'String':
        // For select fields with enum values, default to first value if required
        if (enumValues?.length > 0 && required) {
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
        // Always set current date for autoGenerate and autoUpdate fields
        if (fieldMeta.autoGenerate || fieldMeta.autoUpdate) {
          const now = new Date().toISOString().slice(0, 10); // YYYY-MM-DD format
          return now;
        }
        return null;
      case 'ObjectId':
        return '';
      default:
        return null;
    }
  }
}
