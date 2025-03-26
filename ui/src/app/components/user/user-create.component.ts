import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { ROUTE_CONFIG } from '../../constants';

@Component({
  selector: 'app-user-create',
  standalone: true,
  template: `
    <div class="text-center p-3">
      <h3>Redirecting to Entity Form Component...</h3>
    </div>
  `
})
export class UserCreateComponent {
  constructor(private router: Router) {
    // Redirect to the generic entity form component for creation
    this.router.navigate([ROUTE_CONFIG.getEntityCreateRoute('user')]);
  }
}
