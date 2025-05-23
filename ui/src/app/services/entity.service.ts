import { Injectable } from '@angular/core';
import { MetadataService, FieldMetadata } from './metadata.service';
import { ViewService, ViewMode, VIEW, EDIT, CREATE } from './view.service';
import { FieldOrderService } from './field-order.service';
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
  ) {}

   /**
    * Get the fields that should be displayed for an entity in a specific view mode
    * @param entityName The name of the entity
    * @param currentView The current view mode (VIEW, EDIT, CREATE, SUMMARY)
    * @returns An array of field names to display, ordered according to metadata
    * 
    * Important: Required fields are always included in EDIT and CREATE modes
    * regardless of their displayPages setting
    */
   getViewFields(entityName: string, currentView: string): string[] {
    const metadata = this.metadataService.getEntityMetadata(entityName)
    const allFields = ['_id', ...Object.keys(metadata.fields)];

    const visibleFields = allFields.filter(field => {
      const fieldMetadata = metadata.fields[field]
      // Skip hidden fields
      if (fieldMetadata?.ui?.display === 'hidden') {
        return false
      }
      
      // For edit and create modes, always include required fields regardless of displayPages
      if ((currentView === EDIT || currentView === CREATE) && fieldMetadata?.required) {
        return true;
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
    if (metadata?.type === 'ObjectId') {
        let entity = fieldName.substring(0, fieldName.length - 2) // Remove 'Id' suffix
        let link = `entity/${entity}/${value}`
        if (this.viewService.inSummaryMode(mode)) {
          return `<a href=${link}>View</a>`
        } else if (this.viewService.inViewMode(mode)) {
          return `<a href=${link}>${value}</a>`
        } else if (this.viewService.inEditMode(mode)) {
          return `<a href=${link}>${value}</a>`
        }
        console.error(`Invalid mode for foreign key field: ${mode}`);
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
    
    // Currency handling
    if (metadata?.type === 'Currency' && typeof value === 'number') {
      return this.formatCurrency(value);
    }

    // Default string conversion
    return String(value);
  }

  /**
   * Format currency value with $ sign, comma separators, and two decimal places
   * @param value Numeric value to format
   * @returns Formatted currency string
   */
  private formatCurrency(value: number): string {
    // Use explicit options to ensure consistent formatting
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value);
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
      return this.formatDateMDY(date);
    }
    catch (e) {
      return value;
    }
  }
  
  /**
   * Format a date consistently as MM/DD/YYYY
   * @param date The date to format
   * @returns Formatted date string in MM/DD/YYYY format
   */
  formatDateMDY(date: Date | string | null | undefined): string {
    if (!date) {
      return '';
    }
    
    let dateObj: Date;
    if (typeof date === 'string') {
      // Handle single-digit month/day in various formats
      const dateStr = String(date).trim();
      
      // Try to parse the date
      dateObj = new Date(dateStr);
      
      // If parsing fails, we could add more specific handling here
    } else {
      dateObj = date;
    }
    
    // Check if date is valid
    if (isNaN(dateObj.getTime())) {
      return '';
    }
    
    // Format as MM/DD/YYYY with padding for single digits
    const month = String(dateObj.getMonth() + 1).padStart(2, '0'); // Ensure 2 digits
    const day = String(dateObj.getDate()).padStart(2, '0'); // Ensure 2 digits
    const year = dateObj.getFullYear();
    
    return `${month}/${day}/${year}`;
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
        // For boolean fields, always return false as default
        // This ensures they are included in forms but don't block validation
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
