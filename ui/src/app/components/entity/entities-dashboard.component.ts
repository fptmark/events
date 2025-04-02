import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { AllEntitiesService, AllEntitiesMetadata } from '../../services/all-entities.service';
import { CommonModule } from '@angular/common';

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
              <h5 class="card-title">{{ allEntitiesService.getTitle(entity.entity) }}</h5>
              <p class="card-text">{{ allEntitiesService.getDescription(entity.entity) }}</p>
              <button class="btn btn-primary" (click)="navigateToEntity(entity.entity)">
                {{ allEntitiesService.getButtonLabel(entity.entity) }}
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
  entityTypes: AllEntitiesMetadata[] = [];
  loading: boolean = true;
  error: string = '';

  constructor(
    public allEntitiesService: AllEntitiesService,
    private router: Router
  ) {}

  ngOnInit(): void {
    console.log('EntitiesDashboardComponent: Initializing');
    
    // Wait for entities to be loaded
    this.allEntitiesService.waitForEntities()
      .then(() => {
        // Now we can safely get the entities
        this.entityTypes = this.allEntitiesService.getAvailableEntities();
        console.log('EntitiesDashboardComponent: Entities loaded:', this.entityTypes.length);
        
        // Show error if no entities found
        if (this.entityTypes.length === 0) {
          console.log('EntitiesDashboardComponent: No entities found');
          this.error = 'No entities found. Please refresh the page.';
        }
        
        // Data is ready to display
        this.loading = false;
      })
      .catch(error => {
        console.error('EntitiesDashboardComponent: Error loading entities:', error);
        this.error = 'Error loading entities. Please refresh the page.';
        this.loading = false;
      });
  }


  navigateToEntity(entityType: string): void {
    this.allEntitiesService.addRecent(entityType)
    this.router.navigate(['/entity', entityType]);
  }
}