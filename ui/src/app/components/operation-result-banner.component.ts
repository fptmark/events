import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';

export type OperationResultType = 'success' | 'error' | 'info';

@Component({
  selector: 'operation-result-banner',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div *ngIf="message" [class]="getBannerClass()" class="operation-banner">
      <div class="banner-content">
        <span [class]="getIconClass()"></span>
        <span class="banner-message">{{ message }}</span>
        <button type="button" class="banner-close" (click)="dismiss()">
          <span>&times;</span>
        </button>
      </div>
    </div>
  `,
  styles: [`
    .operation-banner {
      margin-bottom: 16px;
      border-radius: 4px;
      border: 1px solid;
      animation: slideDown 0.3s ease-out;
    }
    
    .banner-content {
      display: flex;
      align-items: center;
      padding: 12px 16px;
      gap: 8px;
    }
    
    .banner-message {
      flex: 1;
      font-weight: 500;
    }
    
    .banner-close {
      background: none;
      border: none;
      font-size: 20px;
      font-weight: bold;
      cursor: pointer;
      opacity: 0.7;
      padding: 0;
      width: 20px;
      height: 20px;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    
    .banner-close:hover {
      opacity: 1;
    }
    
    /* Success styling */
    .success {
      background-color: #d4edda;
      border-color: #c3e6cb;
      color: #155724;
    }
    
    .success .banner-close {
      color: #155724;
    }
    
    /* Error styling */
    .error {
      background-color: #f8d7da;
      border-color: #f5c6cb;
      color: #721c24;
    }
    
    .error .banner-close {
      color: #721c24;
    }
    
    /* Info styling */
    .info {
      background-color: #d1ecf1;
      border-color: #bee5eb;
      color: #0c5460;
    }
    
    .info .banner-close {
      color: #0c5460;
    }
    
    /* Icons */
    .icon {
      font-weight: bold;
      font-size: 16px;
    }
    
    .icon-success::before {
      content: '✓';
    }
    
    .icon-error::before {
      content: '✗';
    }
    
    .icon-info::before {
      content: 'ℹ';
    }
    
    @keyframes slideDown {
      from {
        opacity: 0;
        transform: translateY(-10px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }
  `]
})
export class OperationResultBannerComponent {
  @Input() message: string | null = null;
  @Input() type: OperationResultType = 'success';
  @Output() dismissed = new EventEmitter<void>();

  getBannerClass(): string {
    return `operation-banner ${this.type}`;
  }

  getIconClass(): string {
    return `icon icon-${this.type}`;
  }

  dismiss(): void {
    this.dismissed.emit();
  }
}