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
  expandable?: boolean;
  expanded?: boolean;
  notifications?: any[];
  responseData?: any[];
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
   * Handle backend API response - UNIFIED FORMAT ONLY
   * Expected format: {status: "error|warning|success", notifications: {entity_id: {errors: [], warnings: []}}}
   */
  handleApiResponse(response: any): void {
    this.clear();

    // Handle simple string errors
    if (typeof response === 'string') {
      this.showError(response);
      return;
    }

    // Don't show notification for success with no notifications
    if (response.status === 'success' && !response.notifications) {
      return;
    }

    // Handle unified entity-grouped format
    if (response.status && response.notifications) {
      const messages: string[] = [];
      const allNotifications: any[] = [];
      let totalErrors = 0;
      let totalWarnings = 0;

      // Extract all errors and warnings from all entities
      Object.entries(response.notifications).forEach(([entityId, entityNotif]: [string, any]) => {
        if (entityNotif.errors && Array.isArray(entityNotif.errors)) {
          entityNotif.errors.forEach((error: any) => {
            totalErrors++;
            allNotifications.push({
              ...error,
              level: 'error',
              entity_id: entityId
            });
            // Only add to banner if no field (field-specific errors show under field only)
            if (!error.field && !messages.includes(error.message)) {
              messages.push(error.message);
            }
          });
        }

        if (entityNotif.warnings && Array.isArray(entityNotif.warnings)) {
          entityNotif.warnings.forEach((warning: any) => {
            totalWarnings++;
            allNotifications.push({
              ...warning,
              level: 'warning',
              entity_id: entityId
            });
            // Only add to banner if no field (field-specific warnings show under field only)
            if (!warning.field && !messages.includes(warning.message)) {
              messages.push(warning.message);
            }
          });
        }
      });

      // Add request warnings if present
      if (response.request_warnings && Array.isArray(response.request_warnings)) {
        response.request_warnings.forEach((warning: any) => {
          totalWarnings++;
          allNotifications.push({
            ...warning,
            level: 'warning'
          });
          if (!messages.includes(warning.message)) {
            messages.push(warning.message);
          }
        });
      }

      // Determine notification type based on status
      let notificationType: NotificationType;
      switch (response.status) {
        case 'error':
          notificationType = NOTIFICATION_ERROR;
          break;
        case 'warning':
          notificationType = NOTIFICATION_WARNING;
          break;
        case 'success':
          notificationType = NOTIFICATION_SUCCESS;
          break;
        default:
          notificationType = NOTIFICATION_INFO;
      }

      // If no banner messages but we have field errors, add generic summary
      if (messages.length === 0 && totalErrors > 0) {
        messages.push('Please fix the errors highlighted below');
      } else if (messages.length === 0 && totalWarnings > 0) {
        messages.push('Please review the warnings highlighted below');
      }

      // Filter notifications for Details section - only show non-field-specific ones
      // (field-specific errors are already shown under the fields)
      const detailsNotifications = allNotifications.filter(n => !n.field);

      // Show notification with all collected messages
      if (messages.length > 0) {
        this.notificationSubject.next({
          type: notificationType,
          title: this.getNotificationTitle(notificationType),
          messages,
          autoClose: notificationType === NOTIFICATION_SUCCESS,
          expandable: detailsNotifications.length > 0,
          expanded: false,
          notifications: detailsNotifications,
          responseData: response.data
        });

        if (notificationType === NOTIFICATION_SUCCESS) {
          this.setAutoCloseTimer();
        }
      }
      return;
    }

    // Fallback: no valid format detected
    console.warn('Unknown response format:', response);
  }

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
   * Show an error notification - ONLY handles unified notification system format
   * @param error The error response from the server
   */
  showError(error: any): void {
    this.clear();
    
    let notification: Notification;
    
    if (typeof error === 'string') {
      // Simple error message
      notification = {
        type: NOTIFICATION_ERROR,
        title: 'Error',
        messages: [error]
      };
    } else {
      // Handle notification system format ONLY
      // All server responses should now use this format:
      // { data: null, metadata: null, message: "...", level: "error", notifications: [...] }
      this.handleApiResponse(error);
      return;
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
   * Toggle expanded state of current notification
   */
  toggleExpanded(): void {
    const current = this.notificationSubject.value;
    if (current?.expandable) {
      this.notificationSubject.next({
        ...current,
        expanded: !current.expanded
      });
    }
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
   * Map backend level to notification type
   */
  private mapLevelToType(level: string | null): NotificationType {
    switch (level) {
      case 'success': return NOTIFICATION_SUCCESS;
      case 'warning': return NOTIFICATION_WARNING;
      case 'error': return NOTIFICATION_ERROR;
      case 'info': return NOTIFICATION_INFO;
      default: return NOTIFICATION_INFO;
    }
  }

  /**
   * Get notification title based on type
   */
  private getNotificationTitle(type: NotificationType): string {
    switch (type) {
      case NOTIFICATION_SUCCESS: return 'Success';
      case NOTIFICATION_WARNING: return 'Warning';
      case NOTIFICATION_ERROR: return 'Error';
      case NOTIFICATION_INFO: return 'Info';
      default: return 'Notification';
    }
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