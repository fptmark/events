import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { EntityService, Entity, EntityMetadata } from '../../services/entity.service';
import { CommonModule } from '@angular/common';
import { ROUTE_CONFIG } from '../../constants';
import { EntityComponentService } from '../../services/entity-component.service';

@Component({
  selector: 'app-entity-list',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="container mt-4">
      <h2>{{ entityComponent.getTitle(metadata, entityType) }}</h2>
      
      <div *ngIf="entityComponent.isValidOperation(metadata, 'c')">
        <div class="mb-3">
          <button class="btn btn-primary" (click)="navigateToCreate()">{{ entityComponent.getButtonLabel(metadata) }}</button>
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
              <th *ngFor="let field of displayFields">{{ entityComponent.getFieldDisplayName(field, metadata) }}</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let entity of entities">
              <td *ngFor="let field of displayFields" [innerHTML]="entityComponent.formatFieldValue(entity, field, metadata)"></td>
              <td>
                <ng-container *ngIf="entityComponent.isValidOperation(metadata, 'r')">
                  <button class="btn btn-sm btn-info me-2" (click)="viewEntity(entity._id)">View</button>
                </ng-container>
                <ng-container *ngIf="entityComponent.isValidOperation(metadata, 'u')">
                  <button class="btn btn-sm btn-warning me-2" (click)="editEntity(entity._id)">Edit</button>
                </ng-container>
                <ng-container *ngIf="entityComponent.isValidOperation(metadata, 'd')">
                  <button class="btn btn-sm btn-danger me-2" (click)="deleteEntity(entity._id)">Delete</button>
                </ng-container>
                <!-- Custom action buttons -->
                <ng-container *ngFor="let action of getCustomActions(entity)">
                  <button class="btn btn-sm btn-secondary me-2" (click)="executeCustomAction(action.key, entity)">
                    <i *ngIf="action.icon" [class]="action.icon"></i>
                    {{ action.label }}
                  </button>
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
  metadata: EntityMetadata | null = null;
  displayFields: string[] = [];
  loading: boolean = true;
  error: string = '';

  constructor(
    public entityComponent: EntityComponentService,
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
    
    this.entityComponent.loadEntities(this.entityType).subscribe({
      next: (response) => {
        this.entities = response.entities;
        this.metadata = response.metadata;
        this.displayFields = this.entityComponent.initDisplayFields(this.metadata, 'list');
        this.loading = false;
      },
      error: (err) => {
        console.error('Error loading entities:', err);
        this.error = 'Failed to load entities. Please try again later.';
        this.loading = false;
      }
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
    this.router.navigate([ROUTE_CONFIG.getEntityCreateRoute(this.entityType)]);
  }

  viewEntity(id: string): void {
    this.router.navigate([ROUTE_CONFIG.getEntityDetailRoute(this.entityType, id)]);
  }

  editEntity(id: string): void {
    this.router.navigate([ROUTE_CONFIG.getEntityEditRoute(this.entityType, id)]);
  }

  deleteEntity(id: string): void {
    if (confirm('Are you sure you want to delete this item?')) {
      this.entityComponent.deleteEntity(this.entityType, id).subscribe({
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