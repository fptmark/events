import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

// Notification type constants
export const NOTIFICATION_SUCCESS = 'success';
export const NOTIFICATION_ERROR = 'error';
export const NOTIFICATION_WARNING = 'warning';
export const NOTIFICATION_INFO = 'info';

export type NotificationType = typeof NOTIFICATION_SUCCESS | typeof NOTIFICATION_ERROR | typeof NOTIFICATION_WARNING | typeof NOTIFICATION_INFO;

/**
 * Internal error interfaces used throughout the application.
 * This format is protocol-agnostic and suitable for any error source
 * (REST, GraphQL, WebSocket, client-side validation, etc.)
 */

export interface ValidationFailure {
  field: string;
  constraint: string;
  value?: any;
}

export interface ErrorContext {
  error?: string;
  entity?: string;
  invalid_fields?: ValidationFailure[];
  missing_fields?: string[];
  conflicting_fields?: string[];
  [key: string]: any;
}

export interface ErrorDetail {
  message: string;
  error_type: string;
  context?: ErrorContext;
}

export interface Notification {
  type: NotificationType;
  title: string;
  messages: string[];
  error?: ErrorDetail;
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
   * @param message The success message
   * @param autoClose Whether to auto close the notification
   */
  showSuccess(message: string, autoClose: boolean = true): void {
    this.clear();
    
    this.notificationSubject.next({
      type: NOTIFICATION_SUCCESS,
      title: 'Success',
      messages: [message],
      autoClose
    });
    
    if (autoClose) {
      this.setAutoCloseTimer();
    }
  }
  
  /**
   * Show an error notification with rich context
   * @param error The error details or simple message
   */
  showError(error: ErrorDetail | string): void {
    this.clear();
    
    let notification: Notification;
    
    if (typeof error === 'string') {
      // Simple error message - convert to ErrorDetail format
      notification = {
        type: NOTIFICATION_ERROR,
        title: 'Error',
        messages: [error],
        error: {
          message: error,
          error_type: 'error'
        }
      };
    } else {
      // Error detail object
      const messages = error.context?.error ? [error.context.error] : [error.message];
      
      notification = {
        type: NOTIFICATION_ERROR,
        title: 'Error',
        messages: messages,
        error
      };
    }

    this.notificationSubject.next(notification);
  }

  /**
   * Show a warning notification
   * @param message The warning message
   * @param autoClose Whether to auto close the notification
   */
  showWarning(message: string, autoClose: boolean = true): void {
    this.clear();
    
    this.notificationSubject.next({
      type: NOTIFICATION_WARNING,
      title: 'Warning',
      messages: [message],
      autoClose
    });
    
    if (autoClose) {
      this.setAutoCloseTimer();
    }
  }

  /**
   * Show an info notification
   * @param message The info message
   * @param autoClose Whether to auto close the notification
   */
  showInfo(message: string, autoClose: boolean = true): void {
    this.clear();
    
    this.notificationSubject.next({
      type: NOTIFICATION_INFO,
      title: 'Info',
      messages: [message],
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
   * @param error The error details
   * @returns Formatted error message
   */
  formatErrorDetails(error: ErrorDetail): string {
    if (!error?.context) return '';
    
    const details: string[] = [];
    const context = error.context;
    
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