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
  
interface DisplayInfo {
  displayPages: string
  fields: string[]
}
interface RawShowConfig {
  endpoint: string
  displayInfo: DisplayInfo[]
}

export interface ShowConfig {
  endpoint: string
  displayInfo: DisplayInfo
}

export interface FieldMetadata {
  type?: string
  required?: boolean
  autoGenerate?: boolean
  autoUpdate?: boolean
  client_edit?: boolean
  displayPages?: string
  ge?: number
  le?: number
  min_length?: number
  max_length?: number
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
  clientEdit?: boolean
  readOnly?: boolean
  format?: string
  display?: string    // 'hidden', 'secret'
  show?: RawShowConfig
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
    if (fieldName == "_id") {     // auto map internal primary key to Id
      return {"ui" : { "displayName" : "Id"}}
    }
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
  
  /**
   * Gets the raw show configuration for a specific field
   * @param entityType The entity type
   * @param fieldName The field name
   * @param view The view mode to check
   * @returns The show configuration or null if not found
   */
  getShowConfig(entityType: string, fieldName: string, view: string): ShowConfig | null {
    // console.log('getShowConfig called with:', { entityType, fieldName, view });
    
    const fieldMetadata = this.getFieldMetadata(entityType, fieldName);
    
    if (!fieldMetadata?.ui?.show) return null;

    const raw = fieldMetadata.ui.show;
    
    // Find the first displayInfo that matches the view
    const matchingDisplayInfo = raw.displayInfo.find(info => {
      // If displayPages is empty or 'all', it matches all views
      if (!info.displayPages || info.displayPages === '' || info.displayPages === 'all') {
        return true;
      }
      // Otherwise check if the view is in the displayPages string
      return info.displayPages.includes(view);
    });
    
    if (!matchingDisplayInfo) {
      return null;
    }

    const result = {
      endpoint: raw.endpoint,
      displayInfo: matchingDisplayInfo
    };
    // console.log('returning show config:', result);
    return result;
  }
}