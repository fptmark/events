import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { ROUTE_CONFIG } from '../../constants';
import { EntityAttributesService } from '../../services/entity-attributes.service';

@Component({
  selector: 'app-user-list',
  standalone: true,
  template: `
    <div class="text-center p-3">
      <h3>Redirecting to Entity Component...</h3>
    </div>
  `
})
export class UserListComponent {
  constructor(
    private router: Router,
    private entityAttributes: EntityAttributesService
  ) {
    // Configure any user-specific hooks if needed
    const userAttributes = this.entityAttributes.entityAttributes['user'];
    
    // Example of adding a custom beforeCreate hook for users
    userAttributes.beforeCreate = (userData) => {
      console.log('Processing user data in custom beforeCreate hook');
      // Add any validation or transformation logic here
      // For example, ensuring required fields are present
      if (!userData.email || !userData.username) {
        throw new Error('Username and email are required');
      }
      return userData;
    };
    
    // Example of adding a custom beforeDelete hook
    userAttributes.beforeDelete = (userId) => {
      console.log('Checking if user can be deleted:', userId);
      // You could add validation logic here
      // For example, prevent deletion of admin users
      return true; // Allow the deletion to proceed
    };
    
    // Example of adding custom actions for users
    userAttributes.customActions = {
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
    };
    
    // Example of adding a custom column formatter
    userAttributes.columnFormatters = {
      // Format the display of email addresses
      email: (value, user) => {
        return `<a href="mailto:${value}">${value}</a>`;
      },
      // Format username with special styling for admins
      username: (value, user) => {
        return user.isAccountOwner ? `👑 ${value}` : value;
      }
    };
    
    // Redirect to the generic entity list component
    this.router.navigate([ROUTE_CONFIG.getEntityListRoute('user')]);
  }
}
