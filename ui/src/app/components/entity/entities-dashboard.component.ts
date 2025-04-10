import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { MetadataService, EntityMetadata } from '../../services/metadata.service';
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
              <h5 class="card-title">{{ metadataService.getTitle(entity.entity) }}</h5>
              <p class="card-text">{{ metadataService.getDescription(entity.entity) }}</p>
              <button class="btn btn-primary" (click)="navigateToEntity(entity.entity)">
                {{ metadataService.getButtonLabel(entity.entity) }}
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
    public metadataService: MetadataService,
    private router: Router
  ) {}

  ngOnInit(): void {
    console.log('EntitiesDashboardComponent: Initializing');
    
    // MetadataService is guaranteed to be initialized by the AppComponent
    // We can safely get the entities directly
    this.entityTypes = this.metadataService.getAvailableEntities();
    console.log('EntitiesDashboardComponent: Entities loaded:', this.entityTypes.length);
    
    // Data is ready to display - no need for loading state
    this.loading = false;
  }


  navigateToEntity(entityType: string): void {
    this.metadataService.addRecent(entityType)
    this.router.navigate(['/entity', entityType]);
  }
}