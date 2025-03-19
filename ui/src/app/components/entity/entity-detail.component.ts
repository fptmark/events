import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { EntityService, Entity, EntityMetadata } from '../../services/entity.service';
import { CommonModule } from '@angular/common';
import { ROUTE_CONFIG } from '../../constants';

@Component({
  selector: 'app-entity-detail',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="container mt-4">
      <div class="d-flex justify-content-between align-items-center mb-4">
        <h2>{{ entityType | titlecase }} Details</h2>
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
                <dt class="col-sm-3">{{ getFieldDisplayName(field) }}</dt>
                <dd class="col-sm-9">{{ entity ? formatFieldValue(entity, field) : '' }}</dd>
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
  metadata: EntityMetadata | null = null;
  displayFields: string[] = [];
  loading: boolean = true;
  error: string = '';

  constructor(
    private entityService: EntityService,
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
    
    this.entityService.getEntity(this.entityType, this.entityId).subscribe({
      next: (response) => {
        this.entity = response.entity;
        this.metadata = response.metadata;
        this.initDisplayFields();
        this.loading = false;
      },
      error: (err) => {
        console.error('Error loading entity:', err);
        this.error = 'Failed to load entity details. Please try again later.';
        this.loading = false;
      }
    });
  }

  initDisplayFields(): void {
    if (!this.metadata) return;
    
    // Show all fields except those specifically marked as form-only
    this.displayFields = Object.keys(this.metadata.fields).filter(field => {
      const fieldMeta = this.metadata?.fields[field];
      return fieldMeta && fieldMeta.display !== 'form';
    });
  }

  getFieldDisplayName(fieldName: string): string {
    if (!this.metadata) return fieldName;
    return this.metadata.fields[fieldName]?.displayName || fieldName;
  }

  formatFieldValue(entity: Entity, fieldName: string): string {
    if (!entity || entity[fieldName] === undefined || entity[fieldName] === null) {
      return '';
    }
    
    const value = entity[fieldName];
    const fieldType = this.metadata?.fields[fieldName]?.type;
    const widget = this.metadata?.fields[fieldName]?.widget;
    
    // Password field handling - always show masked
    if (fieldName === 'password' || widget === 'password') {
      return '••••••••'; // Mask password
    }
    
    // Format based on field type
    if (fieldType === 'ISODate' && typeof value === 'string') {
      return new Date(value).toLocaleString();
    } else if (fieldType === 'Boolean') {
      return value ? 'Yes' : 'No';
    } else if (fieldType === 'ObjectId') {
      return String(value);
    } else if (Array.isArray(value)) {
      if (value.length === 0) return '(empty array)';
      return value.join(', ');
    } else if (typeof value === 'object') {
      if (Object.keys(value).length === 0) return '(empty object)';
      try {
        return JSON.stringify(value, null, 2);
      } catch (e) {
        return String(value);
      }
    }
    
    return String(value);
  }

  goToEdit(): void {
    this.router.navigate([ROUTE_CONFIG.getEntityEditRoute(this.entityType, this.entityId)]);
  }

  goBack(): void {
    this.router.navigate([ROUTE_CONFIG.getEntityListRoute(this.entityType)]);
  }
}