import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { map, catchError } from 'rxjs/operators';
import { ActivatedRoute, Router } from '@angular/router';
import { ConfigService } from './config.service';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { MetadataService } from './metadata.service';
import { NotificationService, ErrorDetail, ValidationFailure } from './notification.service';
import { RefreshService } from './refresh.service';

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

/**
 * Server error response interface - now consistent for all error types
 */
interface ServerErrorResponse {
  detail: ErrorDetail;
}

@Injectable({
  providedIn: 'root'
})
export class RestService {
  constructor(
    private http: HttpClient,
    private configService: ConfigService,
    private notificationService: NotificationService,
    private refreshService: RefreshService
  ) {}


  private handleError(server_msg: any): Observable<never> {
    console.log('RestService handleError - Complete error:', server_msg);
    console.log('RestService handleError - Status:', server_msg.status);
    
    // Only handle network/system errors - let components handle business logic errors
    const status = server_msg.status;
    
    // Network errors (no response from server)
    if (status === 0 || !server_msg.error) {
      console.log('RestService: Handling network error');
      this.notificationService.clear();
      this.notificationService.showError('Unable to connect to server. Please check your connection.');
      return throwError(() => server_msg);
    }
    
    // Server errors (5xx) - these are system issues, not business logic
    if (status >= 500) {
      console.log('RestService: Handling server error');
      this.notificationService.clear();
      this.notificationService.showError('Server error occurred. Please try again later.');
      return throwError(() => server_msg);
    }
    
    // Business logic errors (4xx) - let components handle these
    console.log('RestService: Passing through business logic error to component');
    return throwError(() => server_msg);
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
    console.log(`RestService: Attempting to create ${entityType}`)
    return this.http.post<Entity>(this.configService.getApiUrl(entityType), entityData).pipe(
      map(response => {
        console.log(`RestService: Successfully created ${entityType}, waiting for consistency`)
        this.notificationService.showSuccess('Entity created successfully.')
        // Add a small delay to allow Elasticsearch to process the creation
        setTimeout(() => {
          console.log(`RestService: Triggering refresh for ${entityType} after delay`)
          this.refreshService.triggerRefresh(entityType)
        }, 1000)
        return response
      }),
      catchError(error => this.handleError(error))
    );
  }

  updateEntity(entityType: string, id: string, entityData: any): Observable<Entity> {
    console.log(`RestService: Attempting to update ${entityType} with id ${id}`)
    const baseUrl = this.configService.getApiUrl(entityType)
    return this.http.put<Entity>(`${baseUrl}/${id}`, entityData).pipe(
      map(response => {
        console.log(`RestService: Successfully updated ${entityType}, waiting for consistency`)
        this.notificationService.showSuccess('Entity updated successfully.')
        // Add a small delay to allow Elasticsearch to process the update
        setTimeout(() => {
          console.log(`RestService: Triggering refresh for ${entityType} after delay`)
          this.refreshService.triggerRefresh(entityType)
        }, 1000)
        return response
      }),
      catchError(error => this.handleError(error))
    );
  }

  deleteEntity(entityType: string, id: string): void {
    if (confirm('Are you sure you want to delete this item?')) {
      console.log(`RestService: Attempting to delete ${entityType} with id ${id}`)
      const baseUrl = this.configService.getApiUrl(entityType)
      this.http.delete(`${baseUrl}/${id}`).pipe(
        catchError(error => this.handleError(error))
      ).subscribe({
        next: () => {
          console.log(`RestService: Successfully deleted ${entityType}, waiting for consistency`)
          this.notificationService.showSuccess('Entity deleted successfully.')
          // Add a small delay to allow Elasticsearch to process the deletion
          setTimeout(() => {
            console.log(`RestService: Triggering refresh for ${entityType} after delay`)
            this.refreshService.triggerRefresh(entityType)
          }, 1000)
        },
        error: (error) => {
          console.error(`RestService: Error deleting ${entityType}:`, error)
          this.handleError(error)
        }
      })
    }
  }
}
