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

export interface Notification {
  type: NotificationType;
  title: string;
  message: string;
  errors?: Array<{field: string, message: string, entityType?: string}>;
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
   * Show an error notification
   * @param message The primary error message
   * @param errors Optional list of detailed validation errors
   * @param entityType Optional entity type for context (helps with field name formatting)
   */
  showError(message: string, errors?: ValidationError[], entityType?: string): void {
    this.clear(); // Clear any existing notification
    
    this.notificationSubject.next({
      type: NOTIFICATION_ERROR,
      title: 'Error',
      message,
      errors: errors?.map(err => ({
        field: err.loc[err.loc.length - 1],
        message: err.msg,
        entityType // Include entity type for context
      }))
    });
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
}