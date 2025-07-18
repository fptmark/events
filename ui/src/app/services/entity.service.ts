import { Injectable } from '@angular/core';
import { MetadataService, FieldMetadata, ShowConfig } from './metadata.service';
import { ModeService, ViewMode, DETAILS, EDIT, CREATE } from './mode.service';
import { FieldOrderService } from './field-order.service';
import { Router } from '@angular/router';
// import { HttpClient } from '@angular/common/http';
// import { Observable, of, forkJoin } from 'rxjs';
// import { map, catchError } from 'rxjs/operators';
// import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
// import currency from 'currency.js';
// import { RestService } from './rest.service';

export interface EntityResponse<> {
  data: [];
  // No metadata in entity responses anymore, it comes from all-entities
}

@Injectable({
  providedIn: 'root'
})
export class EntityService {
  private currentRecordCount: number | null = null;

  constructor(
    private fieldOrderService: FieldOrderService,
    private metadataService: MetadataService,
    private router: Router,
    private modeService: ModeService,
    // private http: HttpClient,
    // private sanitizer: DomSanitizer,
    // private restService: RestService
  ) {}

  setRecordCount(count: number): void {
    this.currentRecordCount = count;
  }

  getCurrentRecordCount(): number | null {
    return this.currentRecordCount;
  }

   /**
    * Get the fields that should be displayed for an entity in a specific view mode
    * @param entityName The name of the entity
    * @param currentView The current view mode (summary, details, edit, create)
    * @returns An array of field names to display, ordered according to metadata
    * 
    * Important: Required fields are always included in EDIT and CREATE modes
    * regardless of their displayPages setting
    */
   getViewFields(entityName: string, currentView: string): string[] {
    const metadata = this.metadataService.getEntityMetadata(entityName);
    const visibleFields = this.modeService.getViewFields(metadata, currentView);
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
    let type = (fieldName === 'id') ? 'text' : metadata?.type || 'text'

    // format Foreign keys and date for non-create modes
    if (type === 'ObjectId') {
      // Check if there's a show config for this field
      const showConfig = metadata?.ui?.show ? this.metadataService.getShowConfig(entityType, fieldName, mode) : null;
      const entity = this._getEndpoint(showConfig?.endpoint, fieldName)
      return this._formatObjectIdHTML(entity, value, value, mode);
    }

    // Date field handling
    if (type === 'Date' || type === 'Datetime') {
      value = this.getDefaultValue(metadata, mode) || value;
        // const isEditMode = this.modeService.inEditMode(mode)
        // const isCreateMode = this.modeService.inCreateMode(mode)

        // if ((isEditMode && metadata?.autoUpdate) || (isCreateMode && (metadata?.autoGenerate || metadata?.autoUpdate))) {
        //   let date_value = new Date().toISOString()
        //   value = type == 'Datetime' ? date_value: date_value.slice(0, 10); 
        // } 

      return this.formatDate(value, mode, type)
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

  formatDate(value: string, mode?: ViewMode, fieldType?: string): string {
    try {
      const date = new Date(value);
      
      // Forms need a specific format for date inputs
      if (mode && (mode === EDIT || mode === CREATE)) {
        if (fieldType === 'Date') {
          // Format as YYYY-MM-DD for HTML date input (date only)
          const year = date.getFullYear();
          const month = String(date.getMonth() + 1).padStart(2, '0');
          const day = String(date.getDate()).padStart(2, '0');
          return `${year}-${month}-${day}`;
        } else if (fieldType === 'Datetime') {
          // Format as YYYY-MM-DDTHH:MM for HTML datetime-local input
          // Use local timezone to match what user sees
          const year = date.getFullYear();
          const month = String(date.getMonth() + 1).padStart(2, '0');
          const day = String(date.getDate()).padStart(2, '0');
          const hours = String(date.getHours()).padStart(2, '0');
          const minutes = String(date.getMinutes()).padStart(2, '0');
          return `${year}-${month}-${day}T${hours}:${minutes}`;
        }
      } 
      
      // For display-only mode, format based on field type
      value = this.formatDateMDY(new Date(value));
      return fieldType === 'Date' ? value : value + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
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

  private getDefaultValue(fieldMeta: any, mode: any): any {
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
      case 'Date':
        // Always set current date for autoGenerate and autoUpdate fields
        if (this._autoGenerate(fieldMeta, mode) || this._autoUpdate(fieldMeta, mode) ) {
          const now = new Date().toISOString().slice(0, 10); // YYYY-MM-DD format
          return now;
        }
        return null;
      case 'Datetime':
        // Always set current datetime for autoGenerate and autoUpdate fields
        if (this._autoGenerate(fieldMeta, mode) || this._autoUpdate(fieldMeta, mode) ) {
          const now = new Date().toISOString(); // Full ISO datetime
          return now;
        }
        return null;
      case 'ObjectId':
        return '';
      default:
        return null;
    }
  }

  /**
   * Formats an ObjectId field value using embedded FK data from server response.
   * @param entityType The type of the entity containing the ObjectId field.
   * @param fieldName The name of the ObjectId field (e.g., 'accountId').
   * @param mode The current view mode (summary, details, edit, create).
   * @param objectId The ObjectId value.
   * @param entity The complete entity object with embedded FK data.
   * @param showConfig Optional: The pre-fetched show configuration for this field and mode.
   * @returns The formatted string display value.
   */
  formatObjectIdValueWithEmbeddedData(entityType: string, fieldName: string, mode: ViewMode, objectId: string | null | undefined, entity: any, showConfig?: ShowConfig | null): string {
    // If no ObjectId value, return empty string
    if (!objectId) {
      return '';
    }

    // If no show config or no fields specified for this mode, return the ObjectId directly
    if (!showConfig || !showConfig.displayInfo[0].fields || showConfig.displayInfo[0].fields.length === 0) {
      return this.formatFieldValue(entityType, fieldName, mode, objectId);
    }

    // Get the FK field name (remove 'Id' suffix)
    const fkFieldName = this._getEndpoint(showConfig.endpoint, fieldName);
    const embeddedData = entity[fkFieldName];

    // If no embedded data available or the FK doesn't exist, return default formatting
    if (!embeddedData || embeddedData.exists == false) {
      return objectId
      // return this.formatFieldValue(entityType, fieldName, mode, objectId);
    }

    // If the FK entity doesn't exist, show as plain text (no link)
    // if (embeddedData.exists === false) {
    //   return objectId; // Just show the ID as plain text
    // }

    const fieldsToDisplay = showConfig.displayInfo[0].fields;
    const formattedValues: string[] = [];

    // Extract and format the specified fields from embedded data
    for (const field of fieldsToDisplay) {
      const value = embeddedData[field];
      if (value !== null && value !== undefined && String(value).trim() !== '') {
        const formatted = this.formatFieldValue(fkFieldName, field, mode, value);
        formattedValues.push(formatted);
      }
    }

    // If no specified fields have data, but we have other data available, use it
    if (formattedValues.length === 0) {
      // Check if there are any non-empty fields in the embedded data (excluding 'exists')
      for (const [key, value] of Object.entries(embeddedData)) {
        if (key !== 'exists' && value !== null && value !== undefined && String(value).trim() !== '') {
          const formatted = this.formatFieldValue(fkFieldName, key, mode, value);
          formattedValues.push(formatted);
        }
      }
    }

    // Determine what to show: use formatted data if available, otherwise use ID or 'View'
    let displayValue: string;
    if (formattedValues.length > 0) {
      // We have actual data to show
      displayValue = formattedValues.join('; ');
    } else {
      // No data fields available - use ID for details mode, 'View' for summary mode
      if (this.modeService.inDetailsMode(mode)) {
        displayValue = objectId;
      } else {
        displayValue = 'View';
      }
    }

    return this._formatObjectIdHTML(fkFieldName, objectId, displayValue, mode);
  }
  _getEndpoint(endPoint: string | undefined, fieldName: string): string {
    return endPoint || fieldName.toLowerCase().replace("id", ""); // Strip 'Id' from field name if no endpoint
  }

  _formatObjectIdHTML(entity: string, id: string, showValue: string, mode: ViewMode): string {
    // Format the ObjectId value as a link with click handler instead of direct href
    if (this.modeService.inSummaryMode(mode)) {
      // Use provided showValue, fallback to 'View' only if empty
      const displayText = showValue || 'View';
      return `<a href="javascript:void(0)" onclick="window.navigateToEntity('${entity}', '${id}')" style="cursor: pointer; color: blue; text-decoration: underline;">${displayText}</a>`
    } else if (this.modeService.inDetailsMode(mode)) {
      // Use provided showValue, fallback to id only if empty
      const displayText = showValue || id;
      return `<a href="javascript:void(0)" onclick="window.navigateToEntity('${entity}', '${id}')" style="cursor: pointer; color: blue; text-decoration: underline;">${displayText}</a>`
    } else if (this.modeService.inEditMode(mode)) {
      return id
    }
    console.error(`Invalid mode for foreign key field: ${mode}`);
    return ''
  }

  _autoGenerate(fieldMeta: FieldMetadata, mode: ViewMode): boolean {
    return fieldMeta!.autoGenerate ?? this.modeService.inCreateMode(mode)
  }

  _autoUpdate(fieldMeta: FieldMetadata, mode: ViewMode): boolean {
    return fieldMeta!.autoUpdate ?? (this.modeService.inEditMode(mode) || this.modeService.inCreateMode(mode))
  }

}
