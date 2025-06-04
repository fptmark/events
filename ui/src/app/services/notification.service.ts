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
  errors?: string[];  // Add array to track multiple errors
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
   * Check if there's an active notification
   */
  hasActiveNotification(): boolean {
    return this.notificationSubject.value !== null;
  }

  /**
   * Add an error to the current notification or create a new one
   */
  private addError(message: string, context?: ErrorContext): void {
    const current = this.notificationSubject.value;
    
    if (current?.type === NOTIFICATION_ERROR) {
      // Add to existing error notification
      const errors = current.errors || [current.message];
      if (!errors.includes(message)) {
        errors.push(message);
      }
      
      this.notificationSubject.next({
        ...current,
        message: errors.join('\n'),
        errors,
        context: context || current.context
      });
    } else {
      // Create new error notification
      this.notificationSubject.next({
        type: NOTIFICATION_ERROR,
        title: 'Error',
        message,
        context,
        errors: [message]
      });
    }
  }
  
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
    let message: string;
    let context: ErrorContext | undefined;
    
    // Case 1: Error response object from backend
    if (typeof messageOrError === 'object' && messageOrError.error?.detail) {
      const errorDetail = messageOrError.error.detail;
      message = errorDetail.message;
      context = errorDetail.context;

      // Handle specific error types
      switch (errorDetail.error_type) {
        case 'not_found':
          message = `${context?.entity || 'Item'} with ID ${context?.id} was not found. It may have been deleted by another user.`;
          break;
        case 'validation_error':
          // Keep existing validation error handling
          break;
        case 'database_error':
          message = `Database error: ${message}`;
          break;
        // Add more specific error types as needed
      }

      this.addError(message, context);
    } else if (typeof messageOrError === 'string') {
      // Case 2: Direct string message
      this.addError(messageOrError);
    } else {
      // Case 3: Unknown error format
      this.addError('An unexpected error occurred. Please try again.');
    }
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