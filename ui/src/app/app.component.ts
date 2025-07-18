import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet, Router } from '@angular/router';
import { MetadataService } from './services/metadata.service'
import { NavigationService } from './services/navigation.service';
import { ConfigService } from './services/config.service';
import { RestService } from './services/rest.service';
import { EntityService } from './services/entity.service';
import { NotificationComponent } from './components/notification.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, CommonModule, NotificationComponent],
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
          <!-- <a class="navbar-brand" routerLink="/">Events Management</a> -->
          <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav" 
            aria-controls="navbarNav" aria-expanded="false" aria-label="Toggle navigation">
            <span class="navbar-toggler-icon"></span>
          </button>
          <div class="collapse navbar-collapse" id="navbarNav">
            <ul class="navbar-nav me-auto">
              <li class="nav-item">
                <a class="nav-link" routerLink="/" routerLinkActive="active" [routerLinkActiveOptions]="{exact: true}">{{ metadataService.getProjectName() }} Management</a>
              </li>
              <li class="nav-item">
                <a class="nav-link" (click)="redirectToServerRoute('docs')" href="javascript:void(0)">OpenApi Docs</a>
              </li>
              <li class="nav-item">
                <a class="nav-link" (click)="redirectToServerRoute('api/metadata')" href="javascript:void(0)">Metadata</a>
              </li>
            </ul>
            <span class="navbar-text text-light">
              <span *ngIf="entityService.getCurrentRecordCount() !== null && router.url.startsWith('/entity/') && router.url.split('/').length === 3">
                Records: {{ entityService.getCurrentRecordCount() }} | 
              </span>
              Database: {{ metadataService.getDatabaseType() }}
            </span>
          </div>
        </div>
      </nav>
      
      <div class="container-fluid py-3">
        <app-notification></app-notification>
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
    .navbar-text {
      font-size: 0.9rem;
      opacity: 0.9;
    }
  `]
})
export class AppComponent implements OnInit {
  initialized = false;
  title = 'ui';

  constructor(
    public metadataService: MetadataService,
    public navigationService: NavigationService,
    private configService: ConfigService,
    private restService: RestService,
    public entityService: EntityService,
    public router: Router
  ) { }

  redirectToServerRoute(route: string) {
    window.open(`${this.configService.config.server_url}/${route}`);
  }

  ngOnInit() {
    console.log('AppComponent: Initializing application');
    
    // Set up global navigation function for ObjectId links
    (window as any).navigateToEntity = (entityType: string, entityId: string) => {
      console.log(`Global navigateToEntity called for ${entityType}/${entityId}`);
      
      // Check if entity exists before navigating
      this.restService.getEntity(entityType, entityId, 'DETAILS').subscribe({
        next: () => {
          // Entity exists, proceed with navigation
          console.log(`Entity ${entityType}/${entityId} exists, navigating`);
          this.router.navigate(['/entity', entityType, entityId]);
        },
        error: (err) => {
          // Entity doesn't exist, show error popup
          const message = err.error?.message || `${entityType} with ID ${entityId} was not found`;
          alert(message);
        }
      });
    };
    
    // Initialize the metadata service - this will load entity data
    this.metadataService.initialize().subscribe({
      next: () => {
        console.log('AppComponent: Metadata loaded');
        this.initialized = true;
        // Set the document title
        document.title = `${this.metadataService.getProjectName()} Management`;
        this.title = this.metadataService.getProjectName();
      },
      error: (err) => {
        console.error('AppComponent: Error loading metadata:', err);
        // Still set initialized to true to let the app continue
        this.initialized = true;
      }
    });
  }
}
