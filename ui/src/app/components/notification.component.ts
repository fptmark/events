import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { 
  NotificationService, 
  Notification, 
  NOTIFICATION_SUCCESS, 
  NOTIFICATION_ERROR, 
  NOTIFICATION_WARNING, 
  NOTIFICATION_INFO 
} from '../services/notification.service';
import { Subscription } from 'rxjs';
import { MetadataService } from '../services/metadata.service';

@Component({
  selector: 'app-notification',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div *ngIf="notification" 
         class="alert mb-4" 
         [ngClass]="getAlertClass()">
        
        <!-- Header with icon and dismiss button -->
        <div class="d-flex justify-content-between align-items-center">
            <div>
                <i class="bi" [ngClass]="getIconClass()"></i>
                <strong class="ms-2">{{ notification.title }}</strong>
            </div>
            <button type="button" class="btn-close" (click)="clearNotification()"></button>
        </div>
        
        <!-- Message -->
        <div class="mt-2">{{ notification.message }}</div>
        
        <!-- Error details with optional expansion -->
        <div *ngIf="notification.type === NOTIFICATION_ERROR && notification.errors && notification.errors.length > 0">
            <button class="btn btn-sm btn-link p-0 mt-2" 
                    (click)="toggleErrorDetails()">
                {{ showErrorDetails ? 'Hide details' : 'Show details' }}
            </button>
            
            <ul *ngIf="showErrorDetails" class="mt-2 mb-0">
                <li *ngFor="let error of notification.errors">
                    <strong>{{ getFieldDisplayName(error.field, error.entityType) }}:</strong> {{ error.message }}
                </li>
            </ul>
        </div>
    </div>
  `,
  styles: [`
    .alert {
      border-radius: 4px;
      box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    .btn-link {
      text-decoration: none;
    }
    .btn-link:hover {
      text-decoration: underline;
    }
  `]
})
export class NotificationComponent implements OnInit, OnDestroy {
  // Expose constants to template
  readonly NOTIFICATION_SUCCESS = NOTIFICATION_SUCCESS;
  readonly NOTIFICATION_ERROR = NOTIFICATION_ERROR;
  readonly NOTIFICATION_WARNING = NOTIFICATION_WARNING;
  readonly NOTIFICATION_INFO = NOTIFICATION_INFO;

  notification: Notification | null = null;
  showErrorDetails = false;
  private subscription: Subscription | null = null;
  
  constructor(
    private notificationService: NotificationService,
    private metadataService: MetadataService
  ) {}
  
  ngOnInit(): void {
    this.subscription = this.notificationService.notification$.subscribe(notification => {
      this.notification = notification;
      // Reset details flag when notification changes
      this.showErrorDetails = false;
    });
  }
  
  ngOnDestroy(): void {
    if (this.subscription) {
      this.subscription.unsubscribe();
    }
  }
  
  getAlertClass(): string {
    if (!this.notification) return '';
    
    switch (this.notification.type) {
      case NOTIFICATION_SUCCESS: return 'alert-success';
      case NOTIFICATION_ERROR: return 'alert-danger';
      case NOTIFICATION_WARNING: return 'alert-warning';
      case NOTIFICATION_INFO: return 'alert-info';
      default: return 'alert-secondary';
    }
  }
  
  getIconClass(): string {
    if (!this.notification) return '';
    
    switch (this.notification.type) {
      case NOTIFICATION_SUCCESS: return 'bi-check-circle-fill';
      case NOTIFICATION_ERROR: return 'bi-exclamation-triangle-fill';
      case NOTIFICATION_WARNING: return 'bi-exclamation-circle-fill';
      case NOTIFICATION_INFO: return 'bi-info-circle-fill';
      default: return 'bi-bell-fill';
    }
  }
  
  clearNotification(): void {
    this.notificationService.clear();
  }
  
  toggleErrorDetails(): void {
    this.showErrorDetails = !this.showErrorDetails;
  }
  
  getFieldDisplayName(fieldName: string, entityType?: string): string {
    // If we have both entity type and metadata service, try to get the field's display name
    if (entityType && this.metadataService) {
      try {
        const fieldMeta = this.metadataService.getFieldMetadata(entityType, fieldName);
        if (fieldMeta?.ui?.displayName) {
          return fieldMeta.ui.displayName;
        }
      } catch (e) {
        // If there's any error getting the field metadata, fall back to formatting
      }
    }
    
    // Format camelCase to Title Case with spaces
    return fieldName.charAt(0).toUpperCase() + fieldName.slice(1).replace(/([A-Z])/g, ' $1');
  }
}