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
  styleUrls: ['./operation-result-banner.component.css']
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