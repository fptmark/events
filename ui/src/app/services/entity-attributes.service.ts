import { Injectable } from '@angular/core';
import { EntityFieldMetadata, EntityMetadata, EntityMetadataResponse } from './entity.service';

/*
// TODO: Hooks will be implemented later
export interface EntityHooks {
  // Standard lifecycle hooks
  beforeCreate?: (entityData: any) => any;  // Hook for pre-create validation/transformation
  beforeUpdate?: (entityData: any) => any;  // Hook for pre-update validation/transformation
  beforeDelete?: (entityId: string) => boolean;  // Hook to confirm/validate deletion
  afterLoad?: (entities: any[]) => any[];  // Hook for post-processing loaded entities
  
  // Custom actions (previously separate from hooks)
  customActions?: {
    [key: string]: {
      label: string;
      icon?: string;
      action: (entity: any) => void;
      condition?: (entity: any) => boolean;  // Optional condition to show the action
    }
  };
  
  // Column formatting for list view
  columnFormatters?: {
    [field: string]: (value: any, entity: any) => string;
  };
}
*/

@Injectable({
  providedIn: 'root'
})
export class EntityAttributesService {
  /*
  // Hooks for entity-specific behavior - commented out for now as we focus on metadata
  private entityHooks: { [key: string]: EntityHooks } = {
    // Example of user hooks that we're keeping
    user: {
      customActions: {
        resetPassword: {
          label: 'Reset Password',
          icon: 'bi bi-key',
          action: (user) => {
            console.log('Reset password for user:', user);
            alert(`Password reset functionality would be implemented here for ${user.username}`);
          },
          condition: (user) => !user.isAccountOwner
        },
        sendWelcome: {
          label: 'Send Welcome',
          icon: 'bi bi-envelope',
          action: (user) => {
            console.log('Sending welcome email to:', user);
            alert(`Welcome email would be sent to ${user.email}`);
          }
        }
      },
      columnFormatters: {
        email: (value, user) => `<a href="mailto:${value}">${value}</a>`,
        username: (value, user) => user.isAccountOwner ? `👑 ${value}` : value
      }
    }
  };
  */

  // Methods to extract UI properties directly from metadata - no storage needed
  
  /**
   * Get entity title from metadata
   * @param metadata The entity metadata from API
   * @returns The title to display for this entity
   */
  getTitle(metadata: EntityMetadata | EntityMetadataResponse | null): string {
    if (!metadata) return '';
    return metadata.ui?.title || metadata.entity;
  }

  /**
   * Get entity description from metadata
   * @param metadata The entity metadata from API
   * @returns The description to display for this entity
   */
  getDescription(metadata: EntityMetadata | EntityMetadataResponse | null): string {
    if (!metadata) return '';
    return metadata.ui?.description || this.getButtonLabel(metadata);
  }

  getButtonLabel(metadata: EntityMetadata | EntityMetadataResponse | null): string {
    if (!metadata) return '';
    return metadata.ui?.buttonLabel || this.getTitle(metadata);
  }

  /**
   * Get operations allowed for this entity
   * @param metadata The entity metadata from API
   * @returns String representing allowed operations ('c'=create, 'r'=read, 'u'=update, 'd'=delete)
   */
  getOperations(metadata: EntityMetadata | null): string {
    if (!metadata) return '';
    return metadata.operations || 'crud';
  }
  
  /**
   * Determine if a field should be displayed in a given view context
   * @param fieldMeta The field metadata
   * @param viewName The view context ('list', 'detail', 'form')
   * @returns Whether the field should be shown in the specified view
   */
  showInView(fieldMetadata: EntityFieldMetadata, view: string): boolean {
    const displayPages = fieldMetadata.displayPages || '';
    return (displayPages !== 'hidden') && (displayPages === '' || displayPages === 'all' || displayPages.includes(view));
  }

  getFieldOptions(fieldMetadata: EntityFieldMetadata): string[] {
    if (!fieldMetadata.options) return [];
    return fieldMetadata.options;
  }

  formatFieldValue(value: any, fieldMetadata: EntityFieldMetadata): string {
    if (value === undefined || value === null) {
      return '';
    }

    // Handle different field types
    switch (fieldMetadata.type) {
      case 'boolean':
        return value ? 'Yes' : 'No';
      case 'date':
        return new Date(value).toLocaleDateString();
      case 'datetime':
        return new Date(value).toLocaleString();
      case 'select':
        const options = this.getFieldOptions(fieldMetadata);
        return options.includes(value) ? value : String(value);
      case 'multiselect':
        const multiOptions = this.getFieldOptions(fieldMetadata);
        const values = Array.isArray(value) ? value : [value];
        return values
          .map(v => multiOptions.includes(v) ? v : String(v))
          .join(', ');
      case 'textarea':
        return value.replace(/\n/g, '<br>');
      default:
        return String(value);
    }
  }

  /**
   * Get the display name for a field from its metadata
   * @param fieldMetadata The field metadata
   * @returns The display name for the field
   */
  getFieldDisplayName(fieldMetadata: EntityFieldMetadata): string {
    return fieldMetadata.displayName || fieldMetadata.ui?.displayName || '';
  }

  getFieldWidget(fieldMetadata: EntityFieldMetadata): string {
    return fieldMetadata.widget || fieldMetadata.ui?.widget || 'text';
  }

  isFieldRequired(fieldMetadata: EntityFieldMetadata): boolean {
    return fieldMetadata.required || false;
  }

  /*
  // Commented out hooks for now - will be implemented later
  
  // Extension point methods
  applyBeforeCreate(entity: string, data: any): any {
    this.initializeEntityAttributes(entity);
    const hook = this.entityAttributes[entity].beforeCreate;
    return hook ? hook(data) : data;
  }

  applyBeforeUpdate(entity: string, data: any): any {
    this.initializeEntityAttributes(entity);
    const hook = this.entityAttributes[entity].beforeUpdate;
    return hook ? hook(data) : data;
  }

  applyBeforeDelete(entity: string, id: string): boolean {
    this.initializeEntityAttributes(entity);
    const hook = this.entityAttributes[entity].beforeDelete;
    return hook ? hook(id) : true;
  }

  applyAfterLoad(entity: string, data: any[]): any[] {
    this.initializeEntityAttributes(entity);
    const hook = this.entityAttributes[entity].afterLoad;
    return hook ? hook(data) : data;
  }
  */

  constructor() {}
}
