import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { API_CONFIG } from '../constants';

export interface Entity {
  _id: string;
  createdAt?: string;
  updatedAt?: string;
  [key: string]: any;
}

export interface EntityMetadata {
  entity: string;
  displayName: string;
  fields: {
    [key: string]: {
      type: string;
      displayName: string;
      display: string;
      displayAfterField: string;
      widget: string;
      required: boolean;
      minLength?: number;
      maxLength?: number;
      pattern?: string;
      options?: string[];
      min?: number;
      max?: number;
    }
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

  constructor(private http: HttpClient) {}

  getEntities(entityType: string): Observable<{ entities: Entity[], metadata: EntityMetadata }> {
    console.log(">> gentEntities using", API_CONFIG.getApiUrl(entityType))
    return this.http.get<EntityResponse<Entity>>(API_CONFIG.getApiUrl(entityType)).pipe(
      map(response => ({
        entities: Array.isArray(response.data) ? response.data : [response.data],
        metadata: response.metadata
      }))
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
    return this.http.post<EntityResponse<Entity>>(API_CONFIG.getApiUrl(entityType), entity).pipe(
      map(response => Array.isArray(response.data) ? response.data[0] : response.data)
    );
  }

  updateEntity(entityType: string, id: string, entity: Entity): Observable<Entity> {
    return this.http.put<EntityResponse<Entity>>(`${API_CONFIG.getApiUrl(entityType)}/${id}`, entity).pipe(
      map(response => Array.isArray(response.data) ? response.data[0] : response.data)
    );
  }

  deleteEntity(entityType: string, id: string): Observable<any> {
    return this.http.delete(`${API_CONFIG.getApiUrl(entityType)}/${id}`);
  }

  getMetadata(entityType: string): Observable<EntityMetadata> {
    return this.http.get<EntityMetadata>(`${API_CONFIG.getApiUrl(entityType)}/metadata`);
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