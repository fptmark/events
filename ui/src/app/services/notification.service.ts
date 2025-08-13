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
   * Handle backend API response with enhanced notification support
   * @param response The backend API response
   */
  handleApiResponse(response: any): void {
    this.clear();
    
    // Handle simple error messages from current backend
    if (typeof response === 'string') {
      this.showError(response);
      return;
    }

    // Handle new entity-grouped format (status: perfect/completed/failed)
    if (response.status) {
      this.handleEntityGroupedResponse(response);
      return;
    }
    
    // Handle direct message/level format (still used for some simple cases)
    if (response.message && response.level && !response.notifications) {
      switch (response.level) {
        case 'success':
          this.showSuccess(response.message);
          break;
        case 'warning':
          this.showWarning(response.message);
          break;
        case 'error':
          this.showError(response.message);
          break;
        default:
          this.showInfo(response.message);
      }
      return;
    }
    
    // Don't show notification for simple success cases
    if (response.level === 'success' && !response.notifications?.length) {
      return;
    }
    
    if (response.message && response.level) {
      const messages: string[] = [response.message];
      
      // Add summary if there are multiple notifications
      if (response.summary && response.notifications?.length > 1) {
        const summaryParts: string[] = [];
        if (response.summary.error > 0) summaryParts.push(`${response.summary.error} error${response.summary.error !== 1 ? 's' : ''}`);
        if (response.summary.warning > 0) summaryParts.push(`${response.summary.warning} warning${response.summary.warning !== 1 ? 's' : ''}`);
        
        if (summaryParts.length > 0) {
          messages.push(`(${summaryParts.join(', ')})`);
        }
      }
      
      // Convert backend notifications to error context format
      let error: ErrorDetail | undefined;
      if (response.notifications?.length) {
        const invalid_fields: ValidationFailure[] = [];
        const allMessages: string[] = [];
        
        response.notifications.forEach((notif: any) => {
          if (notif.field && notif.level === 'error') {
            invalid_fields.push({
              field: notif.field,
              constraint: notif.message
            });
          }
          
          allMessages.push(notif.message);
          
          // Add nested details
          if (notif.details?.length) {
            notif.details.forEach((detail: any) => {
              allMessages.push(`• ${detail.message}`);
            });
          }
        });
        
        // Add detailed messages
        messages.push(...allMessages);
        
        if (invalid_fields.length > 0) {
          error = {
            message: response.message || 'Validation errors occurred',
            error_type: 'ValidationError',
            context: {
              entity: response.notifications[0]?.entity,
              invalid_fields
            }
          };
        }
      }
      
      const notificationType = this.mapLevelToType(response.level);
      const hasDetailedNotifications = response.notifications?.length > 0;
      
      this.notificationSubject.next({
        type: notificationType,
        title: this.getNotificationTitle(notificationType),
        messages,
        error,
        autoClose: notificationType === NOTIFICATION_SUCCESS,
        expandable: hasDetailedNotifications,
        expanded: false,
        notifications: response.notifications || [],
        responseData: response.data
      });
      
      if (notificationType === NOTIFICATION_SUCCESS) {
        this.setAutoCloseTimer();
      }
    }
  }

  /**
   * Handle new entity-grouped response format
   * @param response Response with status: perfect/completed/failed and entity-grouped notifications
   */
  private handleEntityGroupedResponse(response: any): void {
    // Don't show notification for perfect responses
    if (response.status === 'perfect') {
      return;
    }

    const messages: string[] = [];
    const flatNotifications: any[] = [];

    // Create summary message
    if (response.summary) {
      const summary = response.summary;
      const summaryParts: string[] = [];
      
      if (summary.errors > 0) summaryParts.push(`${summary.errors} error${summary.errors !== 1 ? 's' : ''}`);
      if (summary.warnings > 0) summaryParts.push(`${summary.warnings} warning${summary.warnings !== 1 ? 's' : ''}`);
      
      if (summaryParts.length > 0) {
        const statusText = response.status === 'failed' ? 'Failed' : 'Completed with issues';
        messages.push(`${statusText}: ${summaryParts.join(', ')}`);
        
        if (summary.total_entities > 1) {
          const successfulCount = summary.successful || summary.perfect;
          messages.push(`${successfulCount} of ${summary.total_entities} entities processed successfully`);
        }
      }
    }

    // Flatten entity notifications for display
    if (response.notifications) {
      Object.entries(response.notifications).forEach(([entityId, entityNotif]: [string, any]) => {
        // Add entity context to each notification
        [...entityNotif.errors, ...entityNotif.warnings].forEach((notif: any) => {
          flatNotifications.push({
            ...notif,
            level: notif.severity, // Map severity to level for existing UI
            entity_id: entityId === 'null' ? null : entityId,
            entity_type: entityNotif.entity_type
          });
        });
      });
    }

    // Determine notification type based on status
    let notificationType: NotificationType;
    switch (response.status) {
      case 'failed':
        notificationType = NOTIFICATION_ERROR;
        break;
      case 'completed':
        notificationType = NOTIFICATION_WARNING;
        break;
      default:
        notificationType = NOTIFICATION_INFO;
    }

    const hasDetailedNotifications = flatNotifications.length > 0;

    this.notificationSubject.next({
      type: notificationType,
      title: this.getNotificationTitle(notificationType),
      messages,
      autoClose: false, // Don't auto-close when there are issues
      expandable: hasDetailedNotifications,
      expanded: false,
      notifications: flatNotifications,
      responseData: response.data
    });
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