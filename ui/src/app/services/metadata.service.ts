import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { ConfigService } from './config.service';
import { Observable, Subject, BehaviorSubject } from 'rxjs';

export interface Metadata {
  entity: string
  entityLowerCase?: string  // for easier comparison - internal use only
  ui?: {
    title?: string
    buttonLabel?: string
    description?: string
  }
  operations?: string
  fields: {
    [key: string]: FieldMetadata
  }
}
  
export interface FieldMetadata {
  type?: string
  required?: boolean
  autoGenerate?: boolean
  autoUpdate?: boolean
  displayPages?: string
  min?: number
  max?: number
  minLength?: number
  maxLength?: number
  enum?: {
    values?: string[]
    message?: string
  }
  pattern?: {
    regex?: string
    message?: string
  }
  ui?: UiFieldMetata 
}

export interface UiFieldMetata {
  displayName?: string
  displayAfterField?: string
  displayPages?: string
  link?: string
  readOnly?: boolean
  format?: string
  widget?: string
  display?: string
  [key: string]: any
}

@Injectable({
  providedIn: 'root'
})
export class MetadataService {
  private entities: Metadata[] = [];
  private metadataPromise: Promise<void>;
  private recentEntities: string[] = [];

  constructor(
    private http: HttpClient,
    private configService: ConfigService,
  ) {
    // Load metadata once on initialization and cache the promise
    this.metadataPromise = this.loadMetadata();
  }
  
  private loadMetadata(): Promise<void> {
    // Get API URL from config
    const entitiesUrl = this.configService.getApiUrl('metadata');
    console.log('Metadata: Loading entities from:', entitiesUrl);
    
    // Create a promise that will resolve when entities are loaded
    return new Promise<void>((resolve) => {
      this.http.get<Metadata[]>(entitiesUrl).subscribe({
        next: entities => {
          console.log('Metadata: Entities loaded successfully:', entities.length, 'entities');
          this.entities = entities;
          // Normalize entity names for easier lookup
          for (let e of this.entities) {
            e.entityLowerCase = e.entity.toLowerCase();
          }
          resolve();
        },
        error: (error) => {
          console.error('Metadata: Failed to fetch entities:', error);
          this.entities = []; // Ensure entities array is empty on error
          resolve(); // Still resolve the promise even on error
        }
      });
    });
  }
  
  addRecent(entityType: string){
    this.recentEntities = this.recentEntities.filter(item => item !== entityType)
    this.recentEntities.unshift(entityType)
    this.recentEntities = this.recentEntities.slice(0, 3) // Fix: assign the result back
  }

  getRecent(): string[] {
    return this.recentEntities
  }
  
  /**
   * Gets metadata for an entity type from the cache
   * @param entityType The type of entity
   * @returns Promise that resolves to the metadata
   */
  getEntityMetadata(entityName: string): Metadata {
    const metadata =
      this.entities.find(e => e.entity === entityName) ||
      this.entities.find(e => e.entityLowerCase === entityName);
  
    if (!metadata) {
      throw new Error(`No metadata found for entity: ${entityName}`);
    }
  
    return metadata;
  }

  getEntityTypes(): string[] {
    return this.entities.map( e => e.entity)
  }

  getEntityFields(entityType: string): string[] {
    let metadata = this.getEntityMetadata(entityType)
    return Object.keys(metadata.fields)
  }

  getFieldMetadata(entityType: string, fieldName: string): FieldMetadata {
    let metadata = this.getEntityMetadata(entityType)
    if (!metadata.fields[fieldName]) {
      throw new Error(`No metadata found for field: ${fieldName} in entity: ${entityType}`);
    }
    return metadata.fields[fieldName]
  }

  getUiFieldMetadata(entityType: string, fieldName: string): UiFieldMetata {
    return this.getFieldMetadata(entityType, fieldName).ui || {}
  }
  /**
   * Returns a promise that resolves when metadata is loaded
   */
  waitForEntities(): Promise<void> {
    return this.metadataPromise
  }
  
  /**
   * Gets the list of available entities
   * Should only be called after waitForEntities() resolves
   */
  getAvailableEntities(): Metadata[] {
    return this.entities;
  }
  
  getTitle(entityName: string): string {
    let metadata = this.getEntityMetadata(entityName)
    return this.getEntityMetadata(entityName)?.ui?.title || entityName
  }

  getButtonLabel(entityName: string): string {
    return this.getEntityMetadata(entityName)?.ui?.buttonLabel || this.getTitle(entityName)
  }

  getDescription(entityName: string): string {
    return this.getEntityMetadata(entityName)?.ui?.description || this.getButtonLabel(entityName)
  }

  isValidOperation(entityName: string, operation: string): boolean {
    let operations = this.getEntityMetadata(entityName)?.operations || 'crud'
    operations = operations === 'all' ? 'crud' : operations
    return operations.includes(operation)
  }

  // view can be 'details', 'summary' and/or 'form' e.g. 'details|summary'
  getViewFields(entityName: string, currentView: string): string[] {
    let metadata = this.getEntityMetadata(entityName)
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
      const metadata = this.getEntityMetadata(entityName);
      return metadata.fields[fieldName]?.ui?.displayName || fieldName;
    } catch (error) {
      return fieldName;
    }
  }

  formatFieldValue(entityType: string, fieldName: string, view: string, value: any): string {
    if (!value || value === undefined || value === null) {
      return '';
    }

    let metadata = this.getFieldMetadata(entityType, fieldName)
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
  
}