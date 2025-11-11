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
   * Convert API error response to ValidationFailures - UNIFIED FORMAT ONLY
   * Extracts field errors from entity-grouped notifications
   * @param error API response with notifications in format: {notifications: {entity_id: {errors: [], warnings: []}}}
   * @param entityId Optional entity ID to filter errors for specific entity (Option B)
   */
  convertApiErrorToValidationFailures(error: any, entityId?: string): ValidationFailure[] {
    const validationFailures: ValidationFailure[] = [];

    // Handle unified entity-grouped format
    if (error.notifications && typeof error.notifications === 'object') {
      // Iterate through all entity_ids
      Object.entries(error.notifications).forEach(([notifEntityId, entityNotif]: [string, any]) => {
        // If entityId filter provided, only process matching entity
        if (entityId && notifEntityId !== entityId && notifEntityId !== 'general') {
          return; // Skip this entity
        }

        // Extract errors with field information
        if (entityNotif.errors && Array.isArray(entityNotif.errors)) {
          entityNotif.errors.forEach((error: any) => {
            if (error.field) {
              validationFailures.push({
                field: error.field,
                constraint: error.value || error.message || 'Validation error'
              });
            }
          });
        }

        // Extract warnings with field information
        if (entityNotif.warnings && Array.isArray(entityNotif.warnings)) {
          entityNotif.warnings.forEach((warning: any) => {
            if (warning.field) {
              validationFailures.push({
                field: warning.field,
                constraint: warning.value || warning.message || 'Validation warning'
              });
            }
          });
        }
      });
    }

    console.log('Extracted ValidationFailures:', validationFailures);
    return validationFailures;
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
      constraint: this.getValidationMessage(entityType, fieldName, errors) || 'Invalid value'
    };
  }

  private getFieldDisplayName(entityType: string, fieldName: string): string {
    const fieldMeta = this.metadataService.getFieldMetadata(entityType, fieldName);
    return fieldMeta?.ui?.displayName || fieldName;
  }
} 