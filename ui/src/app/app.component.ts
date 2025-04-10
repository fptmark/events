import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { MetadataService } from './services/metadata.service'

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, CommonModule],
  template: `
    <!-- App Loading State -->
    <div *ngIf="!initialized" class="loading-container">
      <div class="loading-content">
        <h2>Loading Application...</h2>
        <div class="spinner-border text-primary" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
      </div>
    </div>

    <!-- App Content - Only shown after initialization -->
    <ng-container *ngIf="initialized">
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
              <li class="nav-item" *ngFor="let entity of metadataService.getRecent()">
                <a class="nav-link" [routerLink]="['/entity', (entity | lowercase) ]" routerLinkActive="active">
                  {{ metadataService.getTitle(entity) }}
                </a>
              </li>
            </ul>
          </div>
        </div>
      </nav>
      
      <div class="container-fluid py-3">
        <router-outlet></router-outlet>
      </div>
    </ng-container>
  `,
  styles: [`
    .container-fluid { 
      padding-left: 15px;
      padding-right: 15px; 
    }
    .loading-container {
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      display: flex;
      justify-content: center;
      align-items: center;
      background-color: #f8f9fa;
      z-index: 9999;
    }
    .loading-content {
      text-align: center;
    }
    .loading-content h2 {
      margin-bottom: 1rem;
      color: #212529;
    }
  `]
})
export class AppComponent implements OnInit {
  title = 'Events Management';
  initialized = false;

  constructor(
    public metadataService: MetadataService,
  ) { }

  ngOnInit() {
    console.log('AppComponent: Initializing application');
    
    // Check if metadata is already initialized (should not happen on first load)
    if (this.metadataService.isInitialized()) {
      console.log('AppComponent: Metadata already initialized');
      this.initialized = true;
      return;
    }
    
    // Initialize the metadata service - this will load entity data
    this.metadataService.initialize().subscribe({
      next: (entities) => {
        console.log('AppComponent: Metadata loaded with', entities.length, 'entities');
        this.initialized = true;
      },
      error: (err) => {
        console.error('AppComponent: Error loading metadata:', err);
        // Still set initialized to true to let the app continue
        this.initialized = true;
      }
    });
  }
}
