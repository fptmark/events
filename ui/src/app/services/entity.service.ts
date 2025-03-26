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

export interface EntityFieldMetadata {
  type: string;  // Only type is required
  displayName?: string;
  display?: string;
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
  // Add a flexible index signature for any other properties
  [key: string]: any;
}

export interface EntityMetadata {
  entity: string;
  displayName: string;
  fields: {
    [key: string]: EntityFieldMetadata
  };
}


export interface EntityResponse<T = Entity> {
  data: T | T[];
  metadata: EntityMetadata;
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
        // Apply the afterLoad hook if available
        entities = this.entityAttributes.applyAfterLoad(entityType, entities);
        return {
          entities: entities,
          metadata: response.metadata
        };
      })
    );
  }
   
  getEntity(entityType: string, id: string): Observable<{ entity: Entity, metadata: EntityMetadata }> {
    return this.http.get<EntityResponse<Entity>>(`${API_CONFIG.getApiUrl(entityType)}/${id}`).pipe(
      map(response => ({
        entity: Array.isArray(response.data) ? response.data[0] : response.data,
        metadata: response.metadata
      }))
    );
  }

  createEntity(entityType: string, entity: Entity): Observable<Entity> {
    // Apply beforeCreate hook if available
    const transformedEntity = this.entityAttributes.applyBeforeCreate(entityType, entity);
    
    return this.http.post<EntityResponse<Entity>>(API_CONFIG.getApiUrl(entityType), transformedEntity).pipe(
      map(response => Array.isArray(response.data) ? response.data[0] : response.data)
    );
  }

  updateEntity(entityType: string, id: string, entity: Entity): Observable<Entity> {
    // Apply beforeUpdate hook if available
    const transformedEntity = this.entityAttributes.applyBeforeUpdate(entityType, entity);
    
    return this.http.put<EntityResponse<Entity>>(`${API_CONFIG.getApiUrl(entityType)}/${id}`, transformedEntity).pipe(
      map(response => Array.isArray(response.data) ? response.data[0] : response.data)
    );
  }

  deleteEntity(entityType: string, id: string): Observable<any> {
    // Apply beforeDelete hook if available - if hook returns false, don't proceed with delete
    if (!this.entityAttributes.applyBeforeDelete(entityType, id)) {
      return new Observable(observer => {
        observer.error(new Error('Delete operation cancelled by validation rule'));
        observer.complete();
      });
    }
    
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

  getAvailableEntities(): Observable<string[]> {
    // This would typically come from an API endpoint that returns all available entity types
    // For now we'll hardcode the entities based on our known endpoints
    return new Observable<string[]>(observer => {
      observer.next(Object.keys(API_CONFIG.endpoints));
      observer.complete();
    });
  }
}