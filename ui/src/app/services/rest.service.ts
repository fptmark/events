import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { map, catchError } from 'rxjs/operators';
import { ActivatedRoute, Router } from '@angular/router';
import { ConfigService } from './config.service';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { MetadataService } from './metadata.service';
import { NotificationService } from './notification.service';

// Base entity interface - all entities must have _id
export interface Entity {
  _id: string;
  [key: string]: any;
}

// List response interface
export interface ListResponse<T> {
  status: string;
  data: T[];
  total: number;
  isEmpty: boolean;
}

// Delete response has message property
export interface DeleteResponse {
  message: string;
}

// Error response from the API
export interface ErrorResponse {
  detail: {
    message: string
    error_type: string
    context?: {
      id?: string
      error?: string
      [key: string]: any
    }
  }
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
    private notificationService: NotificationService
  ) {}

  private handleError(error: any): Observable<never> {
    // Let the notification service handle the error display
    this.notificationService.showError(error);
    return throwError(() => error);
  }

  getEntity(entityType: string, id: string): Observable<Entity> {
    const baseUrl = this.configService.getApiUrl(entityType)
    return this.http.get<Entity>(`${baseUrl}/${id}`).pipe(
      catchError(error => this.handleError(error))
    );
  }

  getEntityList(entityType: string): Observable<Entity[]> {
    return this.http.get<Entity[]>(this.configService.getApiUrl(entityType)).pipe(
      catchError(error => this.handleError(error))
    );
  }

  createEntity(entityType: string, entityData: any): Observable<Entity> {
    return this.http.post<Entity>(this.configService.getApiUrl(entityType), entityData).pipe(
      catchError(error => this.handleError(error))
    );
  }

  updateEntity(entityType: string, id: string, entityData: any): Observable<Entity> {
    const baseUrl = this.configService.getApiUrl(entityType)
    return this.http.put<Entity>(`${baseUrl}/${id}`, entityData).pipe(
      catchError(error => this.handleError(error))
    );
  }

  deleteEntity(entityType: string, id: string, onSuccess?: () => void): void {
    if (confirm('Are you sure you want to delete this item?')) {
      const baseUrl = this.configService.getApiUrl(entityType)
      this.http.delete(`${baseUrl}/${id}`).pipe(
        catchError(error => this.handleError(error))
      ).subscribe({
        next: () => {
          this.notificationService.showSuccess('Entity deleted successfully.');
          if (onSuccess) {
            onSuccess();
          }
        }
      });
    }
  }
  
}
