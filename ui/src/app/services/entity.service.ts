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
    private metadataService: MetadataService,
    private sanitizer: DomSanitizer,
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
  // getFieldDisplayName(fieldName: string): string {
  //   return fieldName
  // }

  // getFieldWidget(fieldName: string): string {
  //   return 'text'
  // }

  // getFieldOptions(fieldName: string): string[] {
  //   return []
  // }

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