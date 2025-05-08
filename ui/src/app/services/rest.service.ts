import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { ActivatedRoute, Router } from '@angular/router';
import { ConfigService } from './config.service';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { MetadataService } from './metadata.service';

// Base entity interface - all entities must have _id
export interface Entity {
  _id: string;
  [key: string]: any;
}

// Delete response has message property
export interface DeleteResponse {
  message: string;
}

// Error response from the API
export interface ErrorResponse {
  detail: string | ValidationError[];
}

// Validation error format from FastAPI
export interface ValidationError {
  loc: string[];
  msg: string;
  type: string;
}

@Injectable({
  providedIn: 'root'
})

export class RestService {
  constructor(
    private http: HttpClient,
    private configService: ConfigService,
  ) {}

  getEntity(entityType: string, id: string): Observable<Entity> {
    return this.http.get<Entity>(`${this.configService.getApiUrl(entityType)}/${id}`);
  }

  getEntityList(entityType: string): Observable<Entity[]> {
    return this.http.get<Entity[]>(`${this.configService.getApiUrl(entityType)}`);
  }

  createEntity(entityType: string, entityData: any): Observable<Entity> {
    return this.http.post<Entity>(this.configService.getApiUrl(entityType), entityData);
  }

  updateEntity(entityType: string, id: string, entityData: any): Observable<Entity> {
    return this.http.put<Entity>(`${this.configService.getApiUrl(entityType)}/${id}`, entityData);
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
