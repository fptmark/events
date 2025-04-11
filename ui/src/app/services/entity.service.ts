import { Injectable } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { ConfigService } from './config.service';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { MetadataService } from './metadata.service';

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
  ) {}

   // view can be 'details', 'summary' and/or 'form' e.g. 'details|summary'
   getViewFields(entityName: string, currentView: string): string[] {
    let metadata = this.metadataService.getEntityMetadata(entityName)
    let fields = Object.keys(metadata.fields).filter(field => {
      let fieldMetadata = metadata.fields[field]
      if (fieldMetadata?.ui?.display === 'hidden') {
        return false
      }
      let views = fieldMetadata.ui?.displayPages || ''
      return views.includes(currentView) || views === '' || views === 'all'
    })
    return fields
  }

  getFieldDisplayName(entityName: string, fieldName: string): string {
    try {
      const metadata = this.metadataService.getEntityMetadata(entityName);
      return metadata.fields[fieldName]?.ui?.displayName || fieldName;
    } catch (error) {
      return fieldName;
    }
  }

  formatFieldValue(entityType: string, fieldName: string, view: string, value: any): string {
    if (!value || value === undefined || value === null) {
      return '';
    }

    let metadata = this.metadataService.getFieldMetadata(entityType, fieldName)
    let type = metadata?.type || 'text'
    let format = metadata?.ui?.format || ''

    // auto compute format and widget info
    if (type === 'ISODate'){
      if (view === 'summary'){
        format = format || 'short'
      }
    }
    
    // Handle date strings (ISO format)
    if (metadata?.ui?.link){
      let link = metadata.ui.link.replace('${value}', value)
      return `<a href=${link}>View</a>`

    } else if (type === 'ISODate'){
      try {
        const date = new Date(value);
        return format === 'short' ? date.toLocaleDateString() : date.toLocaleString()
      } catch (e) {
        return value;
      }
    } else if (typeof value === 'boolean') {
      return value ? 'Yes' : 'No';
    } else if (typeof value === 'object' && value !== null) {
      return JSON.stringify(value);
    } 
    return String(value);
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

}
