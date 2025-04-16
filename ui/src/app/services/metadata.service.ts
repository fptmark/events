import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { ConfigService } from './config.service';
import { Observable, of } from 'rxjs';
import { tap, catchError } from 'rxjs/operators';

export interface EntityMetadata {
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
  readOnly?: boolean
  format?: string
  display?: string    // 'hidden', 'secret'
  [key: string]: any
}

@Injectable({
  providedIn: 'root'
})
export class MetadataService {
  private entities: EntityMetadata[] = [];
  private recentEntities: string[] = [];
  private initialized = false;

  constructor(
    private http: HttpClient,
    private configService: ConfigService,
  ) { }
  
  /**
   * Initialize the metadata service by loading entity data from the server
   * @returns An Observable that completes when metadata is loaded
   */
  initialize(): Observable<EntityMetadata[]> {
    if (this.initialized) {
      console.log('Metadata: Already initialized, returning existing data');
      return of(this.entities);
    }

    // Get API URL from config
    const entitiesUrl = this.configService.getApiUrl('metadata');
    console.log('Metadata: Loading entities from:', entitiesUrl);
    
    // Return the observable so the caller can wait for it
    return this.http.get<EntityMetadata[]>(entitiesUrl).pipe(
      tap(entities => {
        console.log('Metadata: Entities loaded successfully:', entities.length, 'entities');
        this.entities = entities;
        this.initialized = true;
      }),
      catchError(error => {
        console.error('Metadata: Failed to fetch entities:', error);
        this.entities = []; // Ensure entities array is empty on error
        this.initialized = true;
        return of([]); // Return empty array to allow the app to continue
      })
    );
  }
  
  /**
   * Check if the metadata has been initialized
   */
  isInitialized(): boolean {
    return this.initialized;
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
   * @returns The entity metadata
   */
  getEntityMetadata(entityName: string): EntityMetadata {
    // Case-insensitive lookup
    const metadata = this.entities.find(e => e.entity.toLowerCase() === entityName.toLowerCase() )
  
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

  getFieldMetadata(entityType: string, fieldName: string): FieldMetadata | undefined {
    let metadata = this.getEntityMetadata(entityType)
    if (!metadata.fields[fieldName]) {
      console.log(`No metadata found for field: ${fieldName} in entity: ${entityType}`);
      return undefined
    }
    return metadata.fields[fieldName]
  }

  getUiFieldMetadata(entityType: string, fieldName: string): UiFieldMetata {
    return this.getFieldMetadata(entityType, fieldName)?.ui || {}
  }

  
  /**
   * Gets the list of available entities
   * Safe to call after application initialization
   */
  getAvailableEntities(): EntityMetadata[] {
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
}