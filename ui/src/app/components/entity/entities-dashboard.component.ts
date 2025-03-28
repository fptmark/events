import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { EntityService, EntityMetadataResponse } from '../../services/entity.service';
import { CommonModule } from '@angular/common';
import { ROUTE_CONFIG } from '../../constants';
import { EntityComponentService } from '../../services/entity-component.service';

@Component({
  selector: 'app-entities-dashboard',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="container mt-4">
      <h2>{{ dashboardTitle }}</h2>
      
      <div *ngIf="loading" class="text-center">
        <p>Loading...</p>
      </div>
      
      <div *ngIf="error" class="alert alert-danger">
        {{ error }}
      </div>
      
      <div *ngIf="!loading && !error" class="row row-cols-1 row-cols-md-3 g-4 mt-3">
        <div *ngFor="let entity of entities" class="col">
          <div class="card h-100">
            <div class="card-body">
              <h5 class="card-title">{{ entityComponent.getTitle(entity) }}</h5>
              <p class="card-text">{{ entityComponent.getDescription(entity) }}</p>
            </div>
            <div class="card-footer">
              <button (click)="navigateToEntity(entity.entity)" class="btn btn-primary">
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
  `]
})
export class EntitiesDashboardComponent implements OnInit {
  // Entity data
  entities: EntityMetadataResponse[] = [];
  loading: boolean = true;
  error: string = '';
  
  // Customizable text
  dashboardTitle: string = 'Event Manager Dashboard';
  
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
      next: (entities) => {
        this.entities = entities;
        this.loading = false;
      },
      error: (err) => {
        console.error('Error loading entity types:', err);
        this.error = 'Failed to load entity types. Please try again later.';
        this.loading = false;
      }
    });
  }

  navigateToEntity(entityType: string): void {
    this.router.navigate([ROUTE_CONFIG.getEntityListRoute(entityType)]);
  }
}