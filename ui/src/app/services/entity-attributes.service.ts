import { Injectable } from '@angular/core';

export interface EntityAttributes {
  title: string;
  description: string;
  buttonLabel: string;
  // operations: string;
  
  // Hook extension points
  beforeCreate?: (entityData: any) => any;  // Hook for pre-create validation/transformation
  beforeUpdate?: (entityData: any) => any;  // Hook for pre-update validation/transformation
  beforeDelete?: (entityId: string) => boolean;  // Hook to confirm/validate deletion
  afterLoad?: (entities: any[]) => any[];  // Hook for post-processing loaded entities
  
  // Custom action extension points
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

@Injectable({
  providedIn: 'root'
})
export class EntityAttributesService {
  public entityAttributes: { [key: string]: EntityAttributes } = {
    account: {
      title: 'Accounts',
      description: 'Manage Accounts',
      buttonLabel: 'Manage Accounts',
      // operations: 'crud',
      // Custom hooks for account entity
      afterLoad: (accounts) => {
        console.log('Processing accounts in custom afterLoad hook');
        // You could do additional processing here
        return accounts;
      }
    },
    user: {
      title: 'Users',
      description: 'Manage User Profiles',
      buttonLabel: 'Manage Users',
      // operations: 'crud',
      // Custom hooks for user entity
      beforeCreate: (userData) => {
        console.log('Processing user data in custom beforeCreate hook');
        // Add any validation or transformation logic here
        // For example, ensuring required fields are present
        if (!userData.email || !userData.username) {
          throw new Error('Username and email are required');
        }
        return userData;
      },
      beforeDelete: (userId) => {
        console.log('Checking if user can be deleted:', userId);
        // You could add validation logic here
        // For example, prevent deletion of admin users
        return true; // Allow the deletion to proceed
      },
      // Custom actions for users
      customActions: {
        resetPassword: {
          label: 'Reset Password',
          icon: 'bi bi-key',
          action: (user) => {
            console.log('Reset password for user:', user);
            // Here you would implement the actual password reset logic
            alert(`Password reset functionality would be implemented here for ${user.username}`);
          },
          // Only show for non-admin users
          condition: (user) => !user.isAccountOwner
        },
        sendWelcome: {
          label: 'Send Welcome',
          icon: 'bi bi-envelope',
          action: (user) => {
            console.log('Sending welcome email to:', user);
            // Here you would implement sending welcome email
            alert(`Welcome email would be sent to ${user.email}`);
          }
        }
      },
      // Custom formatters for user fields
      columnFormatters: {
        // Format the display of email addresses
        email: (value, user) => {
          return `<a href="mailto:${value}">${value}</a>`;
        },
        // Format username with special styling for admins
        username: (value, user) => {
          return user.isAccountOwner ? `👑 ${value}` : value;
        }
      }
    },
    profile: {
      title: 'Profiles',
      description: 'Manage User preferences and settings',
      buttonLabel: 'Manage Profiles',
      // operations: 'crud'
    },
    tagaffinity: {
      title: 'Tag Affinity',
      description: 'Manage Interest categories',
      buttonLabel: 'Manage Tag Affinities',
      // operations: 'crud'
    },
    event: {
      title: 'Events',
      description: 'Manage Events',
      buttonLabel: 'Manage Events',
      // operations: 'crud'
    },
    userevent: {
      title: 'User Events',
      description: 'Manage User Events and Attendance',
      buttonLabel: 'Manager User Events',
      // operations: 'crud'
    },
    url: {
      title: 'URLs',
      description: 'Manage Web Sites to crawl',
      buttonLabel: 'Manage URLs',
      // operations: 'crud'
    },
    crawl: {
      title: 'Crawls',
      description: 'Review Crawl results',
      buttonLabel: 'Manage Crawls',
      // operations: 'rud'
    }
  };

  getTitle(entity: string) {
    return this.entityAttributes[entity].title;
  }

  getDescription(entity: string) {
    return this.entityAttributes[entity].description;
  }

  getButtonLabel(entity: string) {
    return this.entityAttributes[entity].buttonLabel;
  }

  getOperations(entity: string) {
    return this.entityAttributes[entity].operations;
  }

  // No longer providing displayFields - rely on metadata from API
  getDisplayFields(entity: string): string[] | undefined {
    return undefined; // Always return undefined so components use metadata
  }

  // Extension point methods
  applyBeforeCreate(entity: string, data: any): any {
    const hook = this.entityAttributes[entity].beforeCreate;
    return hook ? hook(data) : data;
  }

  applyBeforeUpdate(entity: string, data: any): any {
    const hook = this.entityAttributes[entity].beforeUpdate;
    return hook ? hook(data) : data;
  }

  applyBeforeDelete(entity: string, id: string): boolean {
    const hook = this.entityAttributes[entity].beforeDelete;
    return hook ? hook(id) : true;
  }

  applyAfterLoad(entity: string, data: any[]): any[] {
    const hook = this.entityAttributes[entity].afterLoad;
    return hook ? hook(data) : data;
  }

  constructor() {}
}
