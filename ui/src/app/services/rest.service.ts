import { Injectable } from '@angular/core'
import { HttpClient } from '@angular/common/http'
import { Observable, throwError } from 'rxjs'
import { map, catchError } from 'rxjs/operators'
import { ConfigService } from './config.service'
import { NotificationService, ErrorDetail } from './notification.service'
import { RefreshService } from './refresh.service'

// Base entity interface - all entities must have _id
export interface Entity {
  _id: string
  [key: string]: any
}

// List response interface
export interface ListResponse<T> {
  status: string
  data: T[]
  total: number
  isEmpty: boolean
}

// Delete response has message property
export interface DeleteResponse {
  message: string
}

/**
 * Server error response interface - unified format
 */
interface ServerErrorResponse {
  detail: {
    message: string
    error_type: string
    entity: string
    invalid_fields: Array<{
      field: string
      message: string
      value: any
    }>
  }
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

  private handleError(error: any): Observable<never> {
    // Clear any existing notifications
    this.notificationService.clear()
    
    // Network errors (no response from server)
    if (error.status === 0 || !error.error) {
      this.notificationService.showError('Unable to connect to server. Please check your connection.')
      return throwError(() => error)
    }
    
    // Server errors (5xx) - these are system issues, not business logic
    if (error.status >= 500) {
      this.notificationService.showError('Server error occurred. Please try again later.')
      return throwError(() => error)
    }
    
    // Business logic errors (4xx) - display the server's error message
    if (error.error?.detail?.message) {
      this.notificationService.showError(error.error.detail.message)
    } else {
      this.notificationService.showError('An error occurred while processing your request.')
    }
    
    return throwError(() => error)
  }

  getEntity(entityType: string, id: string): Observable<Entity> {
    const baseUrl = this.configService.getApiUrl(entityType)
    return this.http.get<Entity>(`${baseUrl}/${id}`).pipe(
      catchError(error => this.handleError(error))
    )
  }

  getEntityList(entityType: string): Observable<Entity[]> {
    return this.http.get<Entity[]>(this.configService.getApiUrl(entityType)).pipe(
      catchError(error => this.handleError(error))
    )
  }

  createEntity(entityType: string, entityData: any): Observable<Entity> {
    return this.http.post<Entity>(this.configService.getApiUrl(entityType), entityData).pipe(
      map(response => {
        this.notificationService.showSuccess('Entity created successfully.')
        setTimeout(() => {
          this.refreshService.triggerRefresh(entityType)
        }, 1000)
        return response
      }),
      catchError(error => this.handleError(error))
    )
  }

  updateEntity(entityType: string, id: string, entityData: any): Observable<Entity> {
    const baseUrl = this.configService.getApiUrl(entityType)
    return this.http.put<Entity>(`${baseUrl}/${id}`, entityData).pipe(
      map(response => {
        this.notificationService.showSuccess('Entity updated successfully.')
        setTimeout(() => {
          this.refreshService.triggerRefresh(entityType)
        }, 1000)
        return response
      }),
      catchError(error => this.handleError(error))
    )
  }

  deleteEntity(entityType: string, id: string): void {
    if (confirm('Are you sure you want to delete this item?')) {
      const baseUrl = this.configService.getApiUrl(entityType)
      this.http.delete(`${baseUrl}/${id}`).pipe(
        catchError(error => this.handleError(error))
      ).subscribe({
        next: () => {
          this.notificationService.showSuccess('Entity deleted successfully.')
          setTimeout(() => {
            this.refreshService.triggerRefresh(entityType)
          }, 1000)
        },
        error: (error) => {
          this.handleError(error)
        }
      })
    }
  }
} 