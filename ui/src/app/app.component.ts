import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { ConfigService } from './services/config.service';
import { AllEntitiesService } from './services/all-entities.service';

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
            <li class="nav-item" *ngFor="let entity of recent">
              <a class="nav-link" [routerLink]="['/entity', (entity | lowercase) ]" routerLinkActive="active">
                {{ getTitle(entity) }}
              </a>
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
export class AppComponent implements OnInit {
  title = 'Events Management';
  recent: string[] = []

  constructor(
    private configService: ConfigService,
    private allEntitiesService: AllEntitiesService
  ) {
  }

  ngOnInit() {
    // Simple initialization
    console.log('AppComponent: App initialized');
    this.recent = this.allEntitiesService.getRecent()
    console.log(this.recent)
  }

  getTitle(entityType: string): string {
    return this.allEntitiesService.getTitle(entityType)
  }
}
