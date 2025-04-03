import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { ConfigService } from './config.service';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { MetadataService } from './metadata.service';

export interface Entity {
  _id: string;
  [key: string]: any;
}

export interface EntityMetadata {
  type: string;
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
}

export interface EntityData {
  [key: string]: any;
}

export interface EntityResponse<T = EntityData> {
  data: T | T[];
  // No metadata in entity responses anymore, it comes from all-entities
}

@Injectable({
  providedIn: 'root'
})
export class EntityService {
  constructor(
    private http: HttpClient,
    private configService: ConfigService,
    private sanitizer: DomSanitizer,
    private allEntitiesService: MetadataService
  ) {}

  initDisplayFields(fields: { [key: string]: EntityMetadata } | null, view: 'list' | 'details' | 'form'): string[] {
    if (!fields) return []
    return Object.keys(fields)
  }

  formatFieldValue(entity: Entity, fieldName: string): SafeHtml {
    if (!entity || entity[fieldName] === undefined || entity[fieldName] === null) {
      return this.sanitizer.bypassSecurityTrustHtml('')
    }
    return this.sanitizer.bypassSecurityTrustHtml(String(entity[fieldName]))
  }

  getFieldDisplayName(fieldName: string): string {
    return fieldName
  }

  getFieldWidget(fieldName: string): string {
    return 'text'
  }

  getFieldOptions(fieldName: string): string[] {
    return []
  }

  getEntity(entityType: string, id: string): Observable<EntityResponse> {
    return this.http.get<EntityResponse>(`${this.configService.getApiUrl(entityType)}/${id}`);
  }

  getEntityList(entityType: string): Observable<EntityResponse> {
    return this.http.get<EntityResponse>(`${this.configService.getApiUrl(entityType)}`);
  }

  createEntity(entityType: string, entityData: any): Observable<EntityResponse> {
    return this.http.post<EntityResponse>(this.configService.getApiUrl(entityType), entityData);
  }

  updateEntity(entityType: string, id: string, entityData: any): Observable<EntityResponse> {
    return this.http.put<EntityResponse>(`${this.configService.getApiUrl(entityType)}/${id}`, entityData);
  }

  deleteEntity(entityType: string, id: string): Observable<any> {
    return this.http.delete(`${this.configService.getApiUrl(entityType)}/${id}`);
  }
}