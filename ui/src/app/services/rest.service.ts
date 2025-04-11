import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { ActivatedRoute, Router } from '@angular/router';
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

export class RestService {
  constructor(
    private http: HttpClient,
    private configService: ConfigService,
  ) {}

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

  // 
  deleteEntity(entityType: string, id: string, onSuccess?: () => void): void {

    if (confirm('Are you sure you want to delete this item?')) {
      this.http.delete(`${this.configService.getApiUrl(entityType)}/${id}`).subscribe({
        next: () => {
          alert('Entity deleted successfully.');
          if (onSuccess) {
            onSuccess();
          }
        },
        error: (err) => {
          console.error('Error deleting entity:', err);
          alert('Failed to delete entity. Please try again later.');
        }
      });
    }
  }
  
}
