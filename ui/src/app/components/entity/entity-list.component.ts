import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { EntityService, Entity } from '../../services/entity.service';
import { AllEntitiesService } from '../../services/all-entities.service';
import { CommonModule } from '@angular/common';
// Removed constants import as constants.ts was removed

@Component({
  selector: 'app-entity-list',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="container mt-4">
      <h2>{{ allEntitiesService.getTitle(entityType) }}</h2>
      
      <div *ngIf="allEntitiesService.isValidOperation(entityType, 'c')">
        <div class="mb-3">
          <button class="btn btn-primary" (click)="navigateToCreate()">{{ allEntitiesService.getButtonLabel(entityType) }}</button>
        </div>
      </div>
      
      <div *ngIf="loading" class="text-center">
        <p>Loading...</p>
      </div>
      
      <div *ngIf="error" class="alert alert-danger">
        {{ error }}
      </div>
      
      <div *ngIf="!loading && !error">
        <table class="table table-striped">
          <thead>
            <tr>
              <th *ngFor="let field of displayFields">{{ field }}</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let entity of entities">
              <td *ngFor="let field of displayFields">{{ entity[field] }}</td>
              <td>
                <ng-container *ngIf="allEntitiesService.isValidOperation(entityType, 'r')">
                  <button class="btn btn-sm btn-info me-2" (click)="viewEntity(entity._id)">View</button>
                </ng-container>
                <ng-container *ngIf="allEntitiesService.isValidOperation(entityType, 'u')">
                  <button class="btn btn-sm btn-warning me-2" (click)="editEntity(entity._id)">Edit</button>
                </ng-container>
                <ng-container *ngIf="allEntitiesService.isValidOperation(entityType, 'd')">
                  <button class="btn btn-sm btn-danger me-2" (click)="deleteEntity(entity._id)">Delete</button>
                </ng-container>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  `,
  styles: [`
    .container { max-width: 1200px; }
  `]
})
export class EntityListComponent implements OnInit {
  entityType: string = '';
  entities: Entity[] = [];
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
      this.loadEntities();
    });
  }

  loadEntities(): void {
    this.loading = true;
    this.error = '';
    
    // Wait for entities to be loaded
    this.allEntitiesService.waitForEntities()
      .then(() => {
        // Now we can safely load the entity data
        this.entityService.getEntityList(this.entityType).subscribe({
          next: (response) => {
            this.entities = Array.isArray(response.data) ? response.data : [response.data];
            
            // Use fields from the first entity
            if (this.entities.length > 0) {
              this.displayFields = Object.keys(this.entities[0] || {});
            }
            
            this.loading = false;
          },
          error: (err) => {
            console.error('Error loading entities:', err);
            this.error = 'Failed to load entities. Please try again later.';
            this.loading = false;
          }
        });
      })
      .catch(error => {
        console.error('Error waiting for entities metadata:', error);
        this.error = 'Failed to load entity metadata. Please refresh the page.';
        this.loading = false;
      });
  }
  
  // Custom actions are not currently implemented in the stateless approach
  getCustomActions(entity: Entity): { key: string, label: string, icon?: string }[] {
    // Will be implemented when hooks are added back
    return [];
  }
  
  executeCustomAction(actionKey: string, entity: Entity): void {
    // Will be implemented when hooks are added back
    console.log(`Custom action ${actionKey} would be executed on entity:`, entity);
  }

  navigateToCreate(): void {
    // Navigate to create page for this entity type
    this.router.navigate(['/entity', this.entityType, 'create']);
  }

  viewEntity(id: string): void {
    // Navigate to detail view for specific entity
    this.router.navigate(['/entity', this.entityType, id]);
  }

  editEntity(id: string): void {
    // Navigate to edit page for specific entity
    this.router.navigate(['/entity', this.entityType, id, 'edit']);
  }

  deleteEntity(id: string): void {
    if (confirm('Are you sure you want to delete this item?')) {
      this.entityService.deleteEntity(this.entityType, id).subscribe({
        next: () => {
          this.loadEntities(); // Reload the list after deletion
        },
        error: (err) => {
          console.error('Error deleting entity:', err);
          alert('Failed to delete entity. Please try again later.');
        }
      });
    }
  }
}