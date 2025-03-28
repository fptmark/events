import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { map, tap } from 'rxjs/operators';
import { API_CONFIG } from '../constants';
import { EntityAttributesService } from './entity-attributes.service';

export interface Entity {
  _id: string;
  createdAt?: string;
  updatedAt?: string;
  [key: string]: any;
}

export interface EntityFieldMetadataUI {
  displayName?: string;
  widget?: string;
  readOnly?: boolean;
}

export interface EntityFieldMetadata {
  type: string;  // Only type is required
  displayName?: string;
  display?: string;
  displayPages?: string;
  displayAfterField?: string;
  widget?: string;
  required?: boolean;
  readOnly?: boolean;
  minLength?: number;
  maxLength?: number;
  pattern?: string;
  options?: string[];
  min?: number;
  max?: number;
  autoGenerate?: boolean;
  autoUpdate?: boolean;
  ui?: EntityFieldMetadataUI;
}

export interface EntityMetadataUI {
  title?: string;
  buttonLabel?: string;
  description?: string;
}

export interface EntityMetadata {
  entity: string;
  displayName: string;
  ui?: EntityMetadataUI;
  operations?: string;
  fields: {
    [key: string]: EntityFieldMetadata
  };
}


export interface EntityResponse<T = Entity> {
  data: T | T[];
  metadata: EntityMetadata;
}

export interface EntityMetadataResponse {
  entity: string;
  displayName: string;
  ui: EntityMetadataUI;
}

@Injectable({
  providedIn: 'root'
})
export class EntityService {

  constructor(
    private http: HttpClient,
    private entityAttributes: EntityAttributesService
  ) {}

  getEntities(entityType: string): Observable<{ entities: Entity[], metadata: EntityMetadata }> {
    console.log(">> getEntities using", API_CONFIG.getApiUrl(entityType));
    return this.http.get<EntityResponse<Entity>>(API_CONFIG.getApiUrl(entityType)).pipe(
      map(response => {
        let entities = Array.isArray(response.data) ? response.data : [response.data];
        
        // TODO: Apply afterLoad hook when hooks are implemented
        // entities = this.entityAttributes.applyAfterLoad(entityType, entities);
        
        return {
          entities: entities,
          metadata: response.metadata
        };
      })
    );
  }
   
  getEntity(entityType: string, id: string): Observable<{ entity: Entity, metadata: EntityMetadata }> {
    return this.http.get<EntityResponse<Entity>>(`${API_CONFIG.getApiUrl(entityType)}/${id}`).pipe(
      map(response => {
        return {
          entity: Array.isArray(response.data) ? response.data[0] : response.data,
          metadata: response.metadata
        };
      })
    );
  }

  createEntity(entityType: string, entity: Entity): Observable<Entity> {
    // TODO: Apply beforeCreate hook when hooks are implemented
    // const transformedEntity = this.entityAttributes.applyBeforeCreate(entityType, entity);
    const transformedEntity = entity;
    
    return this.http.post<EntityResponse<Entity>>(API_CONFIG.getApiUrl(entityType), transformedEntity).pipe(
      map(response => {
        return Array.isArray(response.data) ? response.data[0] : response.data;
      })
    );
  }

  updateEntity(entityType: string, id: string, entity: Entity): Observable<Entity> {
    // TODO: Apply beforeUpdate hook when hooks are implemented
    // const transformedEntity = this.entityAttributes.applyBeforeUpdate(entityType, entity);
    const transformedEntity = entity;
    
    return this.http.put<EntityResponse<Entity>>(`${API_CONFIG.getApiUrl(entityType)}/${id}`, transformedEntity).pipe(
      map(response => {
        return Array.isArray(response.data) ? response.data[0] : response.data;
      })
    );
  }

  deleteEntity(entityType: string, id: string): Observable<any> {
    // TODO: Apply beforeDelete hook when hooks are implemented
    /* 
    if (!this.entityAttributes.applyBeforeDelete(entityType, id)) {
      return new Observable(observer => {
        observer.error(new Error('Delete operation cancelled by validation rule'));
        observer.complete();
      });
    }
    */
    
    return this.http.delete(`${API_CONFIG.getApiUrl(entityType)}/${id}`);
  }

  getMetadata(entityType: string): Observable<EntityMetadata> {
    // Get metadata from the base endpoint - API already includes metadata with the response
    return this.http.get<any>(`${API_CONFIG.getApiUrl(entityType)}`).pipe(
      map(response => {
        if (!response.metadata) {
          console.error('No metadata found in response:', response);
          throw new Error('Metadata not available in the API response');
        }
        
        return response.metadata;
      })
    );
  }
  
  // No longer needed as we're not storing entity attributes
  // The EntityAttributesService now processes metadata directly

  getAvailableEntities(): Observable<EntityMetadataResponse[]> {
    return this.http.get<EntityMetadataResponse[]>('/api/entities').pipe(
      tap(response => {
        console.log('Available entities:', response);
      })
    );
  }
}