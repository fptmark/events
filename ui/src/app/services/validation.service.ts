import { Injectable } from '@angular/core';
import { ValidationErrors } from '@angular/forms';
import { ValidationFailure } from './notification.service';
import { MetadataService } from './metadata.service';

@Injectable({
  providedIn: 'root'
})
export class ValidationService {
  constructor(
    private metadataService: MetadataService
  ) {}

  /**
   * Get validation error message for a field based on its errors
   */
  getValidationMessage(entityType: string, fieldName: string, errors: ValidationErrors | null): string | null {
    if (!errors) return null;

    const displayName = this.getFieldDisplayName(entityType, fieldName);
    
    if (errors['required']) {
      return `${displayName} is required`;
    }
    if (errors['minlength']) {
      return `${displayName} must be at least ${errors['minlength'].requiredLength} characters`;
    }
    if (errors['maxlength']) {
      return `${displayName} cannot exceed ${errors['maxlength'].requiredLength} characters`;
    }
    if (errors['pattern']) {
      return `${displayName} has an invalid format`;
    }
    if (errors['min']) {
      return `${displayName} must be at least ${errors['min'].min}`;
    }
    if (errors['max']) {
      return `${displayName} cannot exceed ${errors['max'].max}`;
    }
    if (errors['currencyFormat']) {
      return errors['currencyFormat'];
    }
    if (errors['server']) {
      return errors['server'];
    }

    return `${displayName} is invalid`;
  }

  /**
   * Convert API error response to ValidationFailures
   * ONLY handles the unified notification system format
   */
  convertApiErrorToValidationFailures(error: any): ValidationFailure[] {
    console.log('DEBUG: convertApiErrorToValidationFailures called with:', error);
    
    // Check for notification system format with field-specific errors and warnings
    if (error.notifications?.length) {
      console.log('DEBUG: Found notifications:', error.notifications);
      
      const validationFailures = error.notifications
        .filter((notif: any) => {
          const hasField = !!notif.field;
          const isErrorOrWarning = notif.level === 'error' || notif.level === 'warning';
          console.log(`DEBUG: Notification - field: ${notif.field}, level: ${notif.level}, message: ${notif.message}, hasField: ${hasField}, isErrorOrWarning: ${isErrorOrWarning}`);
          return hasField && isErrorOrWarning;
        })
        .map((notif: any) => ({
          field: notif.field,
          constraint: notif.message,
          value: notif.value
        }));
      
      console.log('DEBUG: Extracted ValidationFailures:', validationFailures);
      return validationFailures;
    }
    
    console.log('DEBUG: No notifications found');
    return [];
  }

  /**
   * Convert form validation errors to our standard ValidationFailure format
   */
  convertValidationErrors(
    entityType: string,
    fieldName: string,
    errors: ValidationErrors | null,
    value: any
  ): ValidationFailure | null {
    if (!errors) return null;

    return {
      field: fieldName,
      constraint: this.getValidationMessage(entityType, fieldName, errors) || 'Invalid value',
      value: value
    };
  }

  private getFieldDisplayName(entityType: string, fieldName: string): string {
    const fieldMeta = this.metadataService.getFieldMetadata(entityType, fieldName);
    return fieldMeta?.ui?.displayName || fieldName;
  }
} 