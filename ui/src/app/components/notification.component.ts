import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { 
  NotificationService, 
  Notification, 
  NOTIFICATION_SUCCESS, 
  NOTIFICATION_ERROR, 
  NOTIFICATION_WARNING, 
  NOTIFICATION_INFO,
  ErrorContext,
  ValidationFailure
} from '../services/notification.service';
import { Subscription } from 'rxjs';
import { MetadataService } from '../services/metadata.service';
import { Observable } from 'rxjs';

interface NotificationViewModel extends Notification {
  context?: ErrorContext
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
          <button class="close-button" (click)="clear()">×</button>
        </div>
        <div class="notification-content">
          <p>{{ vm.message }}</p>
          
          <!-- Error Details -->
          <ng-container *ngIf="vm.context as context">
            <div class="error-details">
              <!-- Missing Fields -->
              <div *ngIf="context.missing_fields?.length" class="error-section">
                <p class="error-subtitle">Missing Required Fields:</p>
                <ul>
                  <li *ngFor="let field of context.missing_fields">{{ getFieldDisplayName(field) }}</li>
                </ul>
              </div>
              
              <!-- Invalid Fields -->
              <div *ngIf="context.invalid_fields?.length" class="error-section">
                <p class="error-subtitle">Invalid Fields:</p>
                <ul>
                  <li *ngFor="let error of context.invalid_fields">
                    {{ getFieldDisplayName(error.field) }}: {{ error.constraint }}
                    <span *ngIf="error.value" class="error-value">(provided: {{ error.value }})</span>
                  </li>
                </ul>
              </div>
              
              <!-- Unique Constraint Violations -->
              <div *ngIf="context.conflicting_fields?.length" class="error-section">
                <p class="error-subtitle">Duplicate Values Not Allowed:</p>
                <ul>
                  <li *ngFor="let field of context.conflicting_fields">{{ getFieldDisplayName(field) }}</li>
                </ul>
              </div>

              <!-- Generic Error -->
              <div *ngIf="context.error" class="error-section">
                <p class="error-subtitle">Details:</p>
                <p>{{ context.error }}</p>
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
    }
    
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
    
    .error-value {
      color: #666;
      font-style: italic;
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
    this.subscription = this.notification$.subscribe(() => {
      // Reset any component state if needed
    })
  }
  
  ngOnDestroy(): void {
    this.subscription?.unsubscribe()
  }
  
  clear(): void {
    this.notificationService.clear()
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
}