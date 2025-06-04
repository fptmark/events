import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { ValidationError } from './rest.service';

// Notification type constants
export const NOTIFICATION_SUCCESS = 'success';
export const NOTIFICATION_ERROR = 'error';
export const NOTIFICATION_WARNING = 'warning';
export const NOTIFICATION_INFO = 'info';

export type NotificationType = typeof NOTIFICATION_SUCCESS | typeof NOTIFICATION_ERROR | 
                               typeof NOTIFICATION_WARNING | typeof NOTIFICATION_INFO;

export interface ValidationFailure {
  field: string
  value?: any
  constraint: string
}

export interface ValidationErrorItem {
  field?: string
  loc?: string[]
  message?: string
  msg?: string
  value?: any
}

export interface ValidationErrorMap {
  [field: string]: string | { message: string; value?: any }
}

export interface ErrorContext {
  id?: string
  error?: string
  missing_fields?: string[]
  invalid_fields?: ValidationFailure[]
  conflicting_fields?: string[]
  entity?: string
  error_type: string
  [key: string]: any
}

export interface ErrorResponse {
  detail: {
    message: string
    error_type: string
    context?: ErrorContext
  }
}

export interface Notification {
  type: NotificationType;
  title: string;
  message: string;
  context?: ErrorContext;
  autoClose?: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class NotificationService {
  private notificationSubject = new BehaviorSubject<Notification | null>(null);
  public notification$ = this.notificationSubject.asObservable();
  private autoCloseTimer: any = null;
  
  constructor() {}
  
  /**
   * Show a success notification
   * @param message The success message to display
   * @param autoClose Whether to automatically close the notification after a delay (default: true)
   */
  showSuccess(message: string, autoClose: boolean = true): void {
    this.clear(); // Clear any existing notification
    
    this.notificationSubject.next({
      type: NOTIFICATION_SUCCESS,
      title: 'Success',
      message,
      autoClose
    });
    
    if (autoClose) {
      this.setAutoCloseTimer();
    }
  }
  
  /**
   * Show an error notification with rich context
   * @param messageOrError The error message or error response object
   * @param validationErrors Optional validation errors
   * @param entityType Optional entity type for context
   */
  showError(messageOrError: string | any, validationErrors?: ValidationErrorItem[] | ValidationErrorMap, entityType?: string): void {
    this.clear()
    
    let notification: Notification
    
    // Case 1: Error response object from backend
    if (typeof messageOrError === 'object' && messageOrError.error?.detail) {
      notification = {
        type: NOTIFICATION_ERROR,
        title: 'Error',
        message: messageOrError.error.detail.message,
        context: messageOrError.error.detail.context
      }
    }
    // Case 2: Direct message with validation errors
    else if (typeof messageOrError === 'string' && validationErrors) {
      const context: ErrorContext = {
        error_type: 'validation_error',
        entity: entityType
      }

      if (Array.isArray(validationErrors)) {
        // Handle array of validation errors
        context.invalid_fields = validationErrors.map((error: ValidationErrorItem) => ({
          field: error.field || error.loc?.join('.') || '',
          constraint: error.message || error.msg || '',
          value: error.value
        }))
      } else {
        // Handle validation error object
        context.invalid_fields = Object.entries(validationErrors).map(([field, error]) => ({
          field,
          constraint: typeof error === 'string' ? error : error.message || '',
          value: typeof error === 'object' ? error.value : undefined
        }))
      }

      notification = {
        type: NOTIFICATION_ERROR,
        title: 'Validation Error',
        message: messageOrError,
        context
      }
    }
    // Case 3: Simple error message
    else {
      notification = {
        type: NOTIFICATION_ERROR,
        title: 'Error',
        message: typeof messageOrError === 'string' ? messageOrError : 'An unexpected error occurred',
        context: entityType ? { error_type: 'error', entity: entityType } : undefined
      }
    }

    this.notificationSubject.next(notification)
  }
  
  /**
   * Show a warning notification
   * @param message The warning message to display
   */
  showWarning(message: string): void {
    this.clear(); // Clear any existing notification
    
    this.notificationSubject.next({
      type: NOTIFICATION_WARNING,
      title: 'Warning',
      message
    });
  }
  
  /**
   * Show an informational notification
   * @param message The info message to display
   * @param autoClose Whether to automatically close the notification after a delay (default: true)
   */
  showInfo(message: string, autoClose: boolean = true): void {
    this.clear(); // Clear any existing notification
    
    this.notificationSubject.next({
      type: NOTIFICATION_INFO,
      title: 'Information',
      message,
      autoClose
    });
    
    if (autoClose) {
      this.setAutoCloseTimer();
    }
  }
  
  /**
   * Clear the current notification
   */
  clear(): void {
    if (this.autoCloseTimer) {
      clearTimeout(this.autoCloseTimer);
      this.autoCloseTimer = null;
    }
    this.notificationSubject.next(null);
  }
  
  /**
   * Set a timer to automatically clear the notification
   * @param delay The delay in milliseconds (default: 5000)
   */
  private setAutoCloseTimer(delay: number = 5000): void {
    this.autoCloseTimer = setTimeout(() => {
      this.clear();
    }, delay);
  }

  /**
   * Format error details for display
   * @param context The error context
   * @returns Formatted error message
   */
  formatErrorDetails(context: ErrorContext): string {
    if (!context) return '';
    
    const details: string[] = [];
    
    if (context.error) {
      details.push(`Error: ${context.error}`);
    }
    
    if (context.missing_fields?.length) {
      details.push(`Missing fields: ${context.missing_fields.join(', ')}`);
    }
    
    if (context.invalid_fields?.length) {
      details.push('Invalid fields:');
      context.invalid_fields.forEach(failure => {
        details.push(`  ${failure.field}: ${failure.constraint}`);
      });
    }
    
    if (context.conflicting_fields?.length) {
      details.push(`Duplicate values for: ${context.conflicting_fields.join(', ')}`);
    }
    
    return details.join('\n');
  }
}