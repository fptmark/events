import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { EntityService, Entity } from '../../services/entity.service';
import { AllEntitiesService } from '../../services/all-entities.service';
import { CommonModule } from '@angular/common';
// // Removed constants import as constants.ts was removed

@Component({
  selector: 'app-entity-detail',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="container mt-4">
      <div class="d-flex justify-content-between align-items-center mb-4">
        <h2>{{ allEntitiesService.getTitle(entityType) }} Details</h2>
        <div>
          <button class="btn btn-primary me-2" (click)="goToEdit()">Edit</button>
          <button class="btn btn-secondary" (click)="goBack()">Back to List</button>
        </div>
      </div>
      
      <div *ngIf="loading" class="text-center">
        <p>Loading...</p>
      </div>
      
      <div *ngIf="error" class="alert alert-danger">
        {{ error }}
      </div>
      
      <div *ngIf="!loading && !error && entity">
        <div class="card">
          <div class="card-body">
            <dl class="row">
              <ng-container *ngFor="let field of displayFields">
                <dt class="col-sm-3">{{ field }}</dt>
                <dd class="col-sm-9">{{ entity[field] }}</dd>
              </ng-container>
            </dl>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .container { max-width: 900px; }
  `]
})
export class EntityDetailComponent implements OnInit {
  entityType: string = '';
  entityId: string = '';
  entity: Entity | null = null;
  displayFields: string[] = [];
  loading: boolean = true;
  error: string = '';

  constructor(
    private entityService: EntityService,
    public allEntitiesService: AllEntitiesService,
    private route: ActivatedRoute,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.route.params.subscribe(params => {
      this.entityType = params['entityType'];
      this.entityId = params['id'];
      this.loadEntity();
    });
  }

  loadEntity(): void {
    this.loading = true;
    this.error = '';
    
    // Wait for entities to be loaded
    this.allEntitiesService.waitForEntities()
      .then(() => {
        // Load entity data
        this.entityService.getEntity(this.entityType, this.entityId).subscribe({
      next: (response) => {
        this.entity = Array.isArray(response.data) ? response.data[0] : response.data;
        
        // Get fields from service if available
        try {
          this.displayFields = this.allEntitiesService.getEntityFields(this.entityType);
        } catch (error) {
          // Fallback to using entity keys
          this.displayFields = Object.keys(this.entity || {});
        }
        
        this.loading = false;
      },
      error: (err) => {
        console.error('Error loading entity:', err);
        this.error = 'Failed to load entity details. Please try again later.';
        this.loading = false;
      }
    });
      })
      .catch(error => {
        console.error('Error waiting for entities:', error);
        this.error = 'Failed to load entity metadata. Please refresh the page.';
        this.loading = false;
      });
  }

  goToEdit(): void {
    // Navigate to the edit page for this entity
    this.router.navigate(['/entity', this.entityType, this.entityId, 'edit']);
  }

  goBack(): void {
    // Navigate back to the entity list
    this.router.navigate(['/entity', this.entityType]);
  }

  isValidOperation(operation: string): boolean {
    return this.allEntitiesService.isValidOperation(this.entityType, operation);
  }
}