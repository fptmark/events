import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { 
  NotificationService, 
  Notification, 
  NOTIFICATION_SUCCESS, 
  NOTIFICATION_ERROR, 
  NOTIFICATION_WARNING, 
  NOTIFICATION_INFO,
  ErrorDetail,
  ValidationFailure
} from '../services/notification.service';
import { Subscription } from 'rxjs';
import { MetadataService } from '../services/metadata.service';
import { Observable } from 'rxjs';

interface NotificationViewModel extends Notification {
  error?: ErrorDetail
  expandable?: boolean
  expanded?: boolean
  notifications?: any[]
}

@Component({
  selector: 'app-notification',
  standalone: true,
  imports: [CommonModule],
  template: `
    <ng-container *ngIf="notification$ | async as vm">
      <div class="notification-container" [ngClass]="vm.type">
        <div class="notification-header">
          <strong>{{ vm.title }}</strong>
          <button 
            *ngIf="vm.expandable" 
            class="expand-button" 
            (click)="toggleExpanded()"
            [title]="vm.expanded ? 'Hide details' : 'Show details'">
            {{ vm.expanded ? '▼' : '▶' }}
          </button>
          <button class="close-button" (click)="clear()">×</button>
        </div>
        
        <div class="notification-content">
          <!-- Primary Messages -->
          <div class="primary-messages">
            <div *ngFor="let message of vm.messages" class="primary-message">
              {{ message }}
            </div>
          </div>
          
          <!-- Expandable Detailed Notifications -->
          <div *ngIf="vm.expandable && vm.expanded && vm.notifications" class="detailed-notifications">
            <div class="notifications-header">Details:</div>
            
            <!-- Group notifications by type -->
            <div *ngFor="let group of getGroupedNotifications(vm.notifications)" class="notification-group">
              <div class="group-header" [ngClass]="'group-' + group.level">
                <span class="group-icon">{{ getGroupIcon(group.level) }}</span>
                <span class="group-title">{{ getGroupTitle(group.level) }} ({{ group.notifications.length }})</span>
              </div>
              
              <div class="group-items">
                <div *ngFor="let notification of group.notifications" class="notification-item">
                  <div class="item-message">
                    <span *ngIf="notification.field" class="field-label">{{ getFieldDisplayName(notification.field) }}:</span>
                    {{ notification.message }}
                    <span *ngIf="notification.value !== undefined && notification.value !== null" class="field-value">
                      (value: {{ formatValue(notification.value) }})
                    </span>
                  </div>
                  
                  <!-- Nested details -->
                  <div *ngIf="notification.details?.length" class="nested-details">
                    <div *ngFor="let detail of notification.details" class="detail-item">
                      ∟ {{ detail.message }}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Legacy Error Details (for backward compatibility) -->
          <ng-container *ngIf="vm.error?.context as context">
            <div class="error-details">
              <div *ngIf="context.conflicting_fields?.length" class="error-section">
                <p class="error-subtitle">Duplicate Values Not Allowed:</p>
                <ul>
                  <li *ngFor="let field of context.conflicting_fields">{{ getFieldDisplayName(field) }}</li>
                </ul>
              </div>
            </div>
          </ng-container>
        </div>
      </div>
    </ng-container>
  `,
  styles: [`
    .notification-container {
      margin: 10px;
      padding: 15px;
      border-radius: 4px;
      position: relative;
      border: 1px solid;
    }
    
    .notification-header {
      display: flex;
      align-items: center;
      margin-bottom: 10px;
    }
    
    .expand-button {
      margin-left: 10px;
      background: none;
      border: none;
      cursor: pointer;
      font-size: 14px;
      opacity: 0.7;
      padding: 2px 6px;
      border-radius: 3px;
    }
    .expand-button:hover {
      opacity: 1;
      background: rgba(0,0,0,0.1);
    }
    
    .close-button {
      position: absolute;
      right: 10px;
      top: 10px;
      background: none;
      border: none;
      font-size: 20px;
      cursor: pointer;
      opacity: 0.5;
    }
    .close-button:hover {
      opacity: 1;
    }
    
    .primary-messages {
      margin-bottom: 10px;
    }
    
    .primary-message {
      margin-bottom: 5px;
    }
    
    .detailed-notifications {
      margin-top: 15px;
      padding-top: 15px;
      border-top: 1px solid rgba(0,0,0,0.1);
    }
    
    .notifications-header {
      font-weight: bold;
      margin-bottom: 10px;
      color: #333;
    }
    
    .notification-group {
      margin-bottom: 15px;
    }
    
    .group-header {
      display: flex;
      align-items: center;
      padding: 8px 12px;
      border-radius: 4px;
      margin-bottom: 8px;
      font-weight: bold;
    }
    
    .group-icon {
      margin-right: 8px;
      font-size: 16px;
    }
    
    .group-title {
      flex: 1;
    }
    
    .group-error {
      background: #f8d7da;
      color: #721c24;
      border: 1px solid #f5c6cb;
    }
    
    .group-warning {
      background: #fff3cd;
      color: #856404;
      border: 1px solid #ffeeba;
    }
    
    .group-info {
      background: #d1ecf1;
      color: #0c5460;
      border: 1px solid #bee5eb;
    }
    
    .group-success {
      background: #d4edda;
      color: #155724;
      border: 1px solid #c3e6cb;
    }
    
    .group-items {
      padding-left: 20px;
    }
    
    .notification-item {
      margin-bottom: 10px;
      padding: 8px;
      background: rgba(0,0,0,0.02);
      border-radius: 3px;
    }
    
    .item-message {
      margin-bottom: 5px;
    }
    
    .field-label {
      font-weight: bold;
      color: #333;
    }
    
    .field-value {
      color: #666;
      font-style: italic;
      font-size: 0.9em;
    }
    
    .nested-details {
      margin-top: 8px;
      padding-left: 15px;
    }
    
    .detail-item {
      margin-bottom: 3px;
      color: #666;
      font-size: 0.9em;
    }
    
    /* Legacy error details */
    .error-details {
      margin-top: 10px;
      padding: 10px;
      background: rgba(0,0,0,0.05);
      border-radius: 4px;
    }
    
    .error-section {
      margin-bottom: 10px;
    }
    
    .error-subtitle {
      font-weight: bold;
      margin-bottom: 5px;
    }
    
    ul {
      margin: 0;
      padding-left: 20px;
    }
    
    li {
      margin-bottom: 3px;
    }

    .success { background-color: #d4edda; border-color: #c3e6cb; color: #155724; }
    .error { background-color: #f8d7da; border-color: #f5c6cb; color: #721c24; }
    .warning { background-color: #fff3cd; border-color: #ffeeba; color: #856404; }
    .info { background-color: #d1ecf1; border-color: #bee5eb; color: #0c5460; }
  `]
})
export class NotificationComponent implements OnInit, OnDestroy {
  private subscription: Subscription | null = null
  
  constructor(
    private notificationService: NotificationService,
    private metadataService: MetadataService
  ) {}

  get notification$() {
    return this.notificationService.notification$ as Observable<NotificationViewModel>
  }
  
  ngOnInit(): void {
    this.subscription = this.notification$.subscribe((notification) => {
      // Notification received and will be displayed via template
    })
  }
  
  ngOnDestroy(): void {
    this.subscription?.unsubscribe()
  }
  
  clear(): void {
    this.notificationService.clear()
  }
  
  toggleExpanded(): void {
    this.notificationService.toggleExpanded()
  }
  
  getFieldDisplayName(fieldName: string, entityType?: string): string {
    if (entityType && this.metadataService) {
      try {
        const fieldMeta = this.metadataService.getFieldMetadata(entityType, fieldName)
        if (fieldMeta?.ui?.displayName) {
          return fieldMeta.ui.displayName
        }
      } catch (e) {
        // Fall back to formatting if metadata lookup fails
      }
    }
    return fieldName.charAt(0).toUpperCase() + fieldName.slice(1).replace(/([A-Z])/g, ' $1')
  }

  formatValue(value: any): string {
    if (value === null || value === undefined) return '';
    if (typeof value === 'string' && value.length > 50) {
      return value.substring(0, 50) + '...';
    }
    return String(value);
  }

  getGroupedNotifications(notifications: any[]): { level: string, notifications: any[] }[] {
    // Group notifications by level, prioritizing errors first
    const groups = new Map<string, any[]>();
    
    notifications.forEach(notification => {
      const level = notification.level;
      if (!groups.has(level)) {
        groups.set(level, []);
      }
      groups.get(level)!.push(notification);
    });

    // Return in priority order: error, warning, info, success
    const priorityOrder = ['error', 'warning', 'info', 'success'];
    const result: { level: string, notifications: any[] }[] = [];
    
    priorityOrder.forEach(level => {
      if (groups.has(level)) {
        result.push({ level, notifications: groups.get(level)! });
      }
    });

    // Add any other levels not in the priority list
    groups.forEach((notifications, level) => {
      if (!priorityOrder.includes(level)) {
        result.push({ level, notifications });
      }
    });

    return result;
  }

  getGroupIcon(level: string): string {
    switch (level) {
      case 'error': return '❌';
      case 'warning': return '⚠️';
      case 'info': return 'ℹ️';
      case 'success': return '✅';
      default: return '📝';
    }
  }

  getGroupTitle(level: string): string {
    switch (level) {
      case 'error': return 'Errors';
      case 'warning': return 'Warnings';
      case 'info': return 'Information';
      case 'success': return 'Success';
      default: return level.charAt(0).toUpperCase() + level.slice(1);
    }
  }
}