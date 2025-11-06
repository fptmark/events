import { Component, OnInit, OnDestroy } from '@angular/core';
import { Router } from '@angular/router';
import { MetadataService } from '../services/metadata.service';
import { AuthService } from '../services/auth.service';
import { CommonModule } from '@angular/common';
import { NavigationService } from '../services/navigation.service';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-entities-dashboard',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="container-fluid mt-4">
      <h2>{{ metadataService.getProjectName() }} Dashboard</h2>

      <div *ngIf="loading" class="text-center">
        <p>Loading...</p>
      </div>

      <div *ngIf="error" class="alert alert-danger">
        {{ error }}
      </div>

      <div *ngIf="!loading && !error && entityTypes.length === 0 && !hasAuthnService" class="alert alert-info">
        <p>No entities are configured.</p>
      </div>

      <div *ngIf="!loading && !error && entityTypes.length > 0" class="row row-cols-1 row-cols-md-2 row-cols-lg-3 g-4">
        <div *ngFor="let entity of entityTypes" class="col">
          <div class="card h-100">
            <div class="card-body">
              <h5 class="card-title">{{ metadataService.getTitle(entity) }}</h5>
              <p class="card-text">{{ metadataService.getDescription(entity) }}</p>
              <button class="btn btn-primary" (click)="navigateToEntity(entity)">
                {{ metadataService.getButtonLabel(entity) }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .container-fluid { 
      padding-left: 10px;
      padding-right: 10px;
    }
    .card { transition: transform 0.2s; }
    .card:hover { transform: translateY(-5px); }
  `]
})
export class EntitiesDashboardComponent implements OnInit, OnDestroy {
  entityTypes: string[] = [];
  loading: boolean = true;
  error: string = '';
  hasAuthnService: boolean = false;
  private permissionsSubscription?: Subscription;

  constructor(
    public metadataService: MetadataService,
    private authService: AuthService,
    private router: Router,
    private navigationService: NavigationService
  ) {}

  async ngOnInit(): Promise<void> {
    try {
      // Wait for metadata to be initialized
      await this.metadataService.waitForInit();

      // Check if authn service is configured
      this.hasAuthnService = this.authService.getAuthnConfig() !== null;

      // Subscribe to permissions changes
      this.permissionsSubscription = this.authService.permissions.subscribe(() => {
        this.updateVisibleEntities();
      });

      // Initial filter
      this.updateVisibleEntities();
      this.loading = false;
    } catch (err) {
      console.error('Error loading dashboard:', err);
      this.error = 'Failed to load dashboard. Please try again later.';
      this.loading = false;
    }
  }

  ngOnDestroy(): void {
    this.permissionsSubscription?.unsubscribe();
  }

  /**
   * Filter entities based on permissions
   * If no authn service configured, show all entities (public mode)
   * If authn configured but no permissions yet, trigger login automatically
   * If permissions available, show entities based on permission rules:
   *   - Wildcard "*" means show all entities with those permissions
   *   - Otherwise show only entities with non-empty permission strings
   */
  private updateVisibleEntities(): void {
    const allEntities = this.metadataService.getAvailableEntityTypes();

    if (!this.hasAuthnService) {
      // No auth service - show all entities (public mode)
      this.entityTypes = allEntities;
      return;
    }

    const permissions = this.authService.getPermissions();
    if (!permissions) {
      // Auth service exists but no permissions yet - trigger login
      this.entityTypes = [];
      // Automatically show login modal
      this.authService.requestLogin();
      return;
    }

    // Check for wildcard - show all entities if wildcard has permissions
    if (permissions['*'] && permissions['*'] !== '') {
      this.entityTypes = allEntities;
      return;
    }

    // Filter based on entity-specific permissions (case-insensitive)
    this.entityTypes = allEntities.filter(entity => {
      // Case-insensitive lookup in permissions
      const permKey = Object.keys(permissions).find(
        key => key.toLowerCase() === entity.toLowerCase()
      );
      // Show if permission exists and is not empty string
      return permKey && permissions[permKey] && permissions[permKey] !== '';
    });
  }

  navigateToEntity(entityType: string): void {
    this.metadataService.addRecent(entityType);
    this.router.navigate(['/entity', entityType]);
  }
}