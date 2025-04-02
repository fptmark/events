import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { EntityService, Entity, EntityMetadata } from '../../services/entity.service';
import { CommonModule } from '@angular/common';
import { ROUTE_CONFIG } from '../../constants';
import { EntityComponentService } from '../../services/entity-component.service';

@Component({
  selector: 'app-entity-detail',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="container mt-4">
      <div class="d-flex justify-content-between align-items-center mb-4">
        <h2>{{ entityComponent.getTitle(metadata, entityType) }} Details</h2>
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
                <dt class="col-sm-3">{{ entityComponent.getFieldDisplayName(field) }}</dt>
                <dd class="col-sm-9" [innerHTML]="entityComponent.formatFieldValue(entity, field)"></dd>
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
  metadata!: EntityMetadata;
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
      this.entityId = params['id'];
      this.loadEntity();
    });
  }

  loadEntity(): void {
    this.loading = true;
    this.error = '';
    
    this.entityComponent.loadEntity(this.entityType, this.entityId).subscribe({
      next: (response) => {
        this.entity = response.entity;
        this.metadata = response.metadata;
        this.displayFields = Object.keys(this.entity || {});
        this.loading = false;
      },
      error: (err) => {
        console.error('Error loading entity:', err);
        this.error = 'Failed to load entity details. Please try again later.';
        this.loading = false;
      }
    });
  }

  goToEdit(): void {
    this.router.navigate([ROUTE_CONFIG.getEntityEditRoute(this.entityType, this.entityId)]);
  }

  goBack(): void {
    this.router.navigate([ROUTE_CONFIG.getEntityListRoute(this.entityType)]);
  }

  isValidOperation(operation: string): boolean {
    return this.entityComponent.isValidOperation(this.metadata, operation)
  }
}