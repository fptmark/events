import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
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
    private http: HttpClient,
    private configService: ConfigService,
    private sanitizer: DomSanitizer,
  ) {}

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