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

      // If authn configured but no permissions in memory (page refresh), fetch session
      // This will restore permissions from server if session is still valid
      // If session invalid (401), fetchSession will trigger login modal
      if (this.hasAuthnService && !this.authService.getPermissions()) {
        await this.authService.fetchSession();
      }

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
   * Two modes:
   * 1. No authn service → show all entities (public mode)
   * 2. Authn configured → filter using permissions.dashboard array
   *    - No permissions in memory (page refresh) → show all entities
   *    - First API call will trigger 401 → login modal if session invalid
   *    - After login → permissions cached in memory → dashboard filters
   */
  private updateVisibleEntities(): void {
    const allEntities = this.metadataService.getAvailableEntityTypes();

    // Mode 1: No auth service - show all entities (public mode)
    if (!this.hasAuthnService) {
      this.entityTypes = allEntities;
      return;
    }

    // Mode 2: Auth configured - filter by permissions
    // isEntityOnDashboard returns true if no permissions (allows all until login)
    this.entityTypes = allEntities.filter(entity =>
      this.authService.isEntityOnDashboard(entity)
    );
  }

  navigateToEntity(entityType: string): void {
    this.metadataService.addRecent(entityType);
    this.router.navigate(['/entity', entityType]);
  }
}