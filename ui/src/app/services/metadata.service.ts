import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { ConfigService } from './config.service';
import { Observable, Subject, BehaviorSubject } from 'rxjs';

export interface Metadata {
  entity: string
  ui?: {
    title?: string
    buttonLabel?: string
    description?: string
  }
  operations?: string
  fields: {
    [key: string]: {
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
      ui?: {
        displayName?: string
        displayAfterField?: string
        displayPages?: string
        readOnly?: boolean
        widget?: string
        display?: string
      }
      [key: string]: any
    }
  }
}

@Injectable({
  providedIn: 'root'
})
export class MetadataService {
  private entities: Metadata[] = [];
  private entitiesLoaded = false;
  private entitiesLoading = false;
  private loadPromise: Promise<void> | null = null;
  private recentEntities: string[] = []

  constructor(
    private http: HttpClient,
    private configService: ConfigService,
  ) {
    // Load entities when service is initialized
    this.loadMetadata();
  }
  
  private loadMetadata(): void {
    // If already loading or loaded, don't load again
    if (this.entitiesLoading || this.entitiesLoaded) {
      return;
    }
    
    this.entitiesLoading = true;
    
    // Get API URL from config
    const entitiesUrl = this.configService.getApiUrl('metadata');
    console.log('Metadata: Loading entities from:', entitiesUrl);
    
    // Create a promise that will resolve when entities are loaded
    this.loadPromise = new Promise<void>((resolve, reject) => {
      this.http.get<Metadata[]>(entitiesUrl).subscribe({
        next: entities => {
          console.log('Metadata: Entities loaded successfully:', entities.length, 'entities');
          this.entities = entities;
          this.entitiesLoaded = true;
          this.entitiesLoading = false;
          resolve();
        },
        error: (error) => {
          console.error('Metadata: Failed to fetch entities:', error);
          this.entities = []; // Ensure entities array is empty on error
          this.entitiesLoading = false;
          // We still resolve the promise even on error, just with empty entities
          resolve();
        }
      });
    });
  }
  
  addRecent(entityType: string){
    this.recentEntities = this.recentEntities.filter(item => item !== entityType);
    this.recentEntities.unshift(entityType)
    this.recentEntities.slice(0, 3)
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
    const metadata = this.entities.find(e => e.entity === entityName);
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

  /**
   * Returns true if entities have been loaded
   */
  areEntitiesLoaded(): boolean {
    return this.entitiesLoaded;
  }

  /**
   * Returns a promise that resolves when entities are loaded
   */
  waitForEntities(): Promise<void> {
    if (this.entitiesLoaded) {
      return Promise.resolve();
    }
    
    if (!this.entitiesLoading) {
      this.loadMetadata();
    }
    
    return this.loadPromise || Promise.resolve();
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
    // let md = this.getEntityMetadata(entityName)
  //   let ops: string = md?.operations || 'crud'
    let operations = this.getEntityMetadata(entityName)?.operations || 'crud'
    operations = operations === 'all' ? 'crud' : operations
    // let results =  operations.includes(operation)
    return operations.includes(operation)
  }

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

  // showInView(entityName: string, fieldName: string, currentView: string): boolean {
  //   let views = this.getEntityMetadata(entityName)?.fields[fieldName]?.ui?.displayPages || ''
  //   return views.includes(currentView) || views === '' || views === 'all'
  // }
}