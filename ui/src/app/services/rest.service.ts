import { Injectable } from '@angular/core'
import { HttpClient } from '@angular/common/http'
import { Observable, throwError } from 'rxjs'
import { map, catchError } from 'rxjs/operators'
import { ConfigService } from './config.service'
import { NotificationService, ErrorDetail } from './notification.service'
import { RefreshService } from './refresh.service'
import { MetadataService } from './metadata.service'

// Base entity interface - all entities must have id
export interface Entity {
  id: string
  [key: string]: any
}

// List response interface
export interface ListResponse<T> {
  status: string
  data: T[]
  total: number
  isEmpty: boolean
}

// Legacy API response format (deprecated - use BackendApiResponse)
export interface ApiResponse<T = any> {
  data: T
  message: string | null
  level: string | null
}

// Enhanced API response format with notifications
export interface BackendApiResponse<T = any> {
  data: T
  message: string | null
  level: string | null
  notifications?: any[]
  summary?: {
    error: number
    warning: number
    info: number
    success: number
  }
}

// Legacy delete response format (to be removed)
export interface DeleteResponse {
  message: string
}

@Injectable({
  providedIn: 'root'
})
export class RestService {
  constructor(
    private http: HttpClient,
    private configService: ConfigService,
    private notificationService: NotificationService,
    private refreshService: RefreshService,
    private metadataService: MetadataService
  ) {}

  /**
   * Handle API response and delegate notification handling to NotificationService
   */
  private handleApiResponse<T>(response: BackendApiResponse<T>): T {
    // Let NotificationService handle all response formats (legacy and enhanced)
    this.notificationService.handleApiResponse(response);
    return response.data;
  }

  private handleError(error: any): Observable<never> {
    // Clear any existing notifications and let NotificationService handle all error details
    this.notificationService.clear()
    this.notificationService.showError(error)
    return throwError(() => error)
  }

  getEntity(entityType: string, id: string, mode: string): Observable<Entity> {
    const args = this.metadataService.getShowViewParams(entityType, mode)
    const url = this.configService.getApiUrl(`${entityType}/${id}`) + args
    return this.http.get<BackendApiResponse<Entity>>(url).pipe(
      map((response: BackendApiResponse<Entity>) => this.handleApiResponse(response)),
      catchError(error => this.handleError(error))
    )
  }

  getEntityList(entityType: string, mode: string): Observable<Entity[]> {
    const args = this.metadataService.getShowViewParams(entityType, mode)
    return this.http.get<BackendApiResponse<Entity[]>>(this.configService.getApiUrl(entityType + args)).pipe(
      map(response => this.handleApiResponse(response)),
      catchError(error => this.handleError(error))
    )
  }

  createEntity(entityType: string, entityData: any): Observable<Entity> {
    return this.http.post<BackendApiResponse<Entity>>(this.configService.getApiUrl(entityType), entityData).pipe(
      map(response => {
        const data = this.handleApiResponse(response)
        setTimeout(() => {
          this.refreshService.triggerRefresh(entityType)
        }, 1000)
        return data
      }),
      catchError(error => this.handleError(error))
    )
  }

  updateEntity(entityType: string, id: string, entityData: any): Observable<Entity> {
    const baseUrl = this.configService.getApiUrl(entityType)
    return this.http.put<BackendApiResponse<Entity>>(`${baseUrl}/${id}`, entityData).pipe(
      map(response => {
        const data = this.handleApiResponse(response)
        setTimeout(() => {
          this.refreshService.triggerRefresh(entityType)
        }, 1000)
        return data
      }),
      catchError(error => this.handleError(error))
    )
  }

  deleteEntity(entityType: string, id: string): void {
    if (confirm('Are you sure you want to delete this item?')) {
      const baseUrl = this.configService.getApiUrl(entityType)
      this.http.delete<BackendApiResponse<null>>(`${baseUrl}/${id}`).pipe(
        catchError(error => this.handleError(error))
      ).subscribe({
        next: (response) => {
          this.handleApiResponse(response)
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