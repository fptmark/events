import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { ROUTE_CONFIG } from '../../constants';
import { EntityAttributesService } from '../../services/entity-attributes.service';

@Component({
  selector: 'app-account-list',
  standalone: true,
  template: `
    <div class="text-center p-3">
      <h3>Redirecting to Entity Component...</h3>
    </div>
  `
})
export class AccountListComponent {
  constructor(
    private router: Router,
    private entityAttributes: EntityAttributesService
  ) {
    // Configure any account-specific hooks if needed
    const accountAttributes = this.entityAttributes.entityAttributes['account'];
    
    // Example of adding a custom afterLoad hook for accounts
    accountAttributes.afterLoad = (accounts) => {
      console.log('Processing accounts in custom afterLoad hook');
      // You could do additional processing here
      return accounts;
    };
    
    // Redirect to the generic entity list component
    this.router.navigate([ROUTE_CONFIG.getEntityListRoute('account')]);
  }
}
