import { Injectable } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { ConfigService } from './config.service';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { MetadataService, FieldMetadata } from './metadata.service';
import { ViewService, ViewMode, VIEW, EDIT, CREATE } from './view.service';

export interface EntityResponse<> {
  data: [];
  // No metadata in entity responses anymore, it comes from all-entities
}

@Injectable({
  providedIn: 'root'
})
export class EntityService {
  constructor(
    private configService: ConfigService,
    private metadataService: MetadataService,
    private sanitizer: DomSanitizer,
    private router: Router,
    private viewService: ViewService
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
    return this.orderFields(visibleFields, metadata);
  }

  orderFields(fields: string[], metadata: any): string[] {
    const fieldMeta = metadata.fields || {};
    const placed = new Set<string>();
    const chains: Record<string, string[]> = {};  // DFA target -> [fields]
    const dangling: string[] = [];
    const idFields: string[] = [];
    const negativeDFAMap: Record<string, string[]> = {};
    const noDFA: string[] = [];
  
    // Categorize fields
    for (const field of fields) {
      const dfa = fieldMeta[field]?.ui?.displayAfterField ?? '';
      if (dfa.startsWith('-')) {
        if (!negativeDFAMap[dfa]) negativeDFAMap[dfa] = [];
        negativeDFAMap[dfa].push(field);
      } else if (dfa) {
        if (!chains[dfa]) chains[dfa] = [];
        chains[dfa].push(field);
      } else {
        noDFA.push(field);
      }
    }
  
    // Sort chains and negatives
    for (const key in chains) {
      chains[key].sort();
    }
    for (const key in negativeDFAMap) {
      negativeDFAMap[key].sort();
    }
  
    const validFields = new Set(fields);
    for (const start of Object.keys(chains)) {
      if (!validFields.has(start)) {
        dangling.push(...chains[start]);
        delete chains[start];
      }
    }
    dangling.sort();
  
    // Separate Id fields
    for (const field of noDFA) {
      if (field !== '_id' && field.endsWith('Id')) {
        idFields.push(field);
      }
    }
    idFields.sort();
  
    const noDFAFields = noDFA.filter(f => !idFields.includes(f) && f !== '_id').sort();
  
    const ordered: string[] = [];
  
    // Handle _id
    if (fields.includes('_id') && !(fieldMeta['_id']?.ui?.displayAfterField)) {
      ordered.push('_id');
      placed.add('_id');
    }
  
    // Place no-DFA fields
    ordered.push(...noDFAFields);
    noDFAFields.forEach(f => placed.add(f));
  
    // Place Id fields
    ordered.push(...idFields);
    idFields.forEach(f => placed.add(f));
  
    // Place dangling DFAs
    ordered.push(...dangling);
    dangling.forEach(f => placed.add(f));
  
    // Helper to recursively insert chains
    const insertChain = (start: string) => {
      if (placed.has(start)) return;
      ordered.push(start);
      placed.add(start);
      if (chains[start]) {
        for (const next of chains[start]) {
          insertChain(next);
        }
      }
    };

    // Handle negative DFA chains properly
    const sortedNegatives = Object.keys(negativeDFAMap).sort((a, b) => parseInt(a) - parseInt(b));
    for (const neg of sortedNegatives) {
      for (const field of negativeDFAMap[neg]) {
        insertChain(field);
      }
    }

    // Insert remaining DFA chains (non-negative, valid targets)
    for (const start in chains) {
      if (!placed.has(start) && validFields.has(start)) {
        insertChain(start);
      }
    }

    return ordered;
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
      
      // Determine format based on mode
      if (this.viewService.inSummaryMode(mode)) {
        format = format || 'short';
      } else {
        format = format || 'long';
      }
      
      // For edit mode, use current date for auto-update fields
      if (this.viewService.inEditMode(mode)) {
        if (metadata?.autoUpdate) {
          value = new Date().toISOString().substring(0, 16);
        }
      }
      
      // For create mode, use current date for auto-generate/update fields
      if (this.viewService.inCreateMode(mode)) {
        if (metadata?.autoGenerate || metadata?.autoUpdate) {
          value = new Date().toISOString().substring(0, 16); // Format for datetime-local
        }
      }
      
      if (this.viewService.inCreateMode(mode)) {
        return this.getDefaultValue(metadata);
      }

      return this.formatDate(value, format);
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

  formatDate(value: string, format: string): string {
    try{
      const date = new Date(value);
      return format === 'short' ? date.toLocaleDateString() : date.toLocaleString()
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
          const now = new Date().toISOString();
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
