import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { ROUTE_CONFIG } from './constants';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, CommonModule],
  template: `
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
      <div class="container-fluid">
        <a class="navbar-brand" routerLink="/">Events Management</a>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav" 
          aria-controls="navbarNav" aria-expanded="false" aria-label="Toggle navigation">
          <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navbarNav">
          <ul class="navbar-nav">
            <li class="nav-item">
              <a class="nav-link" routerLink="/" routerLinkActive="active" [routerLinkActiveOptions]="{exact: true}">Dashboard</a>
            </li>
            <li class="nav-item">
              <a class="nav-link" routerLink="/entity/user" routerLinkActive="active">Users</a>
            </li>
            <li class="nav-item">
              <a class="nav-link" routerLink="/entity/account" routerLinkActive="active">Accounts</a>
            </li>
          </ul>
        </div>
      </div>
    </nav>
    
    <div class="container-fluid py-3">
      <router-outlet></router-outlet>
    </div>
  `,
  styles: [`
    .container-fluid { 
      padding-left: 15px;
      padding-right: 15px; 
    }
  `]
})
export class AppComponent {
  title = 'Events Management';
}
