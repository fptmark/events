import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { EntityService, EntityMetadata } from '../../services/entity.service';
import { CommonModule } from '@angular/common';
import { ROUTE_CONFIG } from '../../constants';
import { EntityComponentService } from '../../services/entity-component.service';

@Component({
  selector: 'app-entities-dashboard',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="container mt-4">
      <h2>Entity Dashboard</h2>
      
      <div *ngIf="loading" class="text-center">
        <p>Loading...</p>
      </div>
      
      <div *ngIf="error" class="alert alert-danger">
        {{ error }}
      </div>
      
      <div *ngIf="!loading && !error" class="row row-cols-1 row-cols-md-2 row-cols-lg-3 g-4">
        <div *ngFor="let entity of entityTypes" class="col">
          <div class="card h-100">
            <div class="card-body">
              <h5 class="card-title">{{ entityComponent.getTitle(entity, entity.entity) }}</h5>
              <p class="card-text">{{ entityComponent.getDescription(entity) }}</p>
              <button class="btn btn-primary" (click)="navigateToEntity(entity.entity)">
                {{ entityComponent.getButtonLabel(entity) }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .container { max-width: 1200px; }
    .card { transition: transform 0.2s; }
    .card:hover { transform: translateY(-5px); }
  `]
})
export class EntitiesDashboardComponent implements OnInit {
  entityTypes: EntityMetadata[] = [];
  loading: boolean = true;
  error: string = '';

  constructor(
    public entityComponent: EntityComponentService,
    private entityService: EntityService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.loadEntityTypes();
  }

  loadEntityTypes(): void {
    this.loading = true;
    this.error = '';
    
    this.entityService.getAvailableEntities().subscribe({
      next: (metadata) => {
        this.entityTypes = metadata;
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Failed to load entity types. Please try again later.';
        this.loading = false;
      }
    });
  }

  navigateToEntity(entityType: string): void {
    this.router.navigate([ROUTE_CONFIG.getEntityListRoute(entityType)]);
  }
}