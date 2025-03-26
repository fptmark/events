import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { EntityService, Entity, EntityMetadata } from '../../services/entity.service';
import { CommonModule } from '@angular/common';
import { ROUTE_CONFIG } from '../../constants';
import { EntityAttributesService } from '../../services/entity-attributes.service';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { EntityDisplayService } from '../../services/entity-display.service';

@Component({
  selector: 'app-entity-list',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="container mt-4">
      <h2>{{ entityType | titlecase }} List</h2>
      
      <div *ngIf="isValidOperation(entityType, 'c')">
      
        <div class="mb-3">
          <button class="btn btn-primary" (click)="navigateToCreate()">Create New {{ entityType | titlecase }}</button>
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
              <th *ngFor="let field of displayFields">{{ getFieldDisplayName(field) }}</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let entity of entities">
              <td *ngFor="let field of displayFields" [innerHTML]="formatFieldValue(entity, field)"></td>
              <td>
                <ng-container *ngIf="isValidOperation(entityType, 'r')">
                  <button class="btn btn-sm btn-info me-2" (click)="viewEntity(entity._id)">View</button>
                </ng-container>
                <ng-container *ngIf="isValidOperation(entityType, 'u')">
                  <button class="btn btn-sm btn-warning me-2" (click)="editEntity(entity._id)">Edit</button>
                </ng-container>
                <ng-container *ngIf="isValidOperation(entityType, 'd')">
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
    private entityAttributes: EntityAttributesService,
    private entityService: EntityService,
    private entityDisplay: EntityDisplayService,
    private route: ActivatedRoute,
    private router: Router,
    private sanitizer: DomSanitizer
  ) {}

  ngOnInit(): void {
    this.route.params.subscribe(params => {
      this.entityType = params['entityType'];
      this.loadEntities();
    });
  }

  isValidOperation(entityType: string, operation: string): boolean {
    return this.entityAttributes.getOperations(entityType).includes(operation)
  }

  loadEntities(): void {
    this.loading = true;
    this.error = '';
    
    this.entityService.getEntities(this.entityType).subscribe({
      next: (response) => {
        this.entities = response.entities;
        this.metadata = response.metadata;
        this.initDisplayFields();
        this.loading = false;
      },
      error: (err) => {
        console.error('Error loading entities:', err);
        this.error = 'Failed to load entities. Please try again later.';
        this.loading = false;
      }
    });
  }

  initDisplayFields(): void {
    // if (!this.metadata) return;
    if (!this.metadata) return;
    
    // Use the display service to determine which fields to show based on metadata
    this.displayFields = Object.keys(this.metadata.fields).filter(field => {
      const fieldMeta = this.metadata?.fields[field];
      if (!fieldMeta) return false;
      
      // Use the display service to check field visibility
      return this.entityDisplay.showInView(fieldMeta, 'summary');
    });
    
  }

  getFieldDisplayName(fieldName: string): string {
    if (!this.metadata) return fieldName;
    return this.metadata.fields[fieldName]?.displayName || fieldName;
  }

  formatFieldValue(entity: Entity, fieldName: string): SafeHtml {
    if (!entity || entity[fieldName] === undefined || entity[fieldName] === null) {
      return this.sanitizer.bypassSecurityTrustHtml('');
    }
    
    // Check if there's a custom formatter for this field
    const customFormatter = this.entityAttributes.entityAttributes[this.entityType]?.columnFormatters?.[fieldName];
    if (customFormatter) {
      const formattedValue = customFormatter(entity[fieldName], entity);
      return this.sanitizer.bypassSecurityTrustHtml(formattedValue);
    }
    
    const value = entity[fieldName];
    const fieldMeta = this.metadata?.fields[fieldName];
    const fieldType = fieldMeta?.type;
    const widget = fieldMeta?.widget;
    let displayValue = '';
    
    // Format based on field widget type
    if (widget === 'password') {
      displayValue = '••••••••'; // Mask password
    }
    // Format based on field type
    else if (fieldType === 'ISODate' && (typeof value === 'string' || value instanceof Date)) {
      const date = typeof value === 'string' ? new Date(value) : value;
      displayValue = isNaN(date.getTime()) ? String(value) : date.toLocaleString();
    } 
    else if (fieldType === 'Boolean') {
      displayValue = value ? 'Yes' : 'No';
    } 
    else if (fieldType === 'ObjectId') {
      // Truncate long IDs for better display
      const strValue = String(value);
      displayValue = strValue.length > 10 ? strValue.substring(0, 7) + '...' : strValue;
    } 
    else if (Array.isArray(value)) {
      if (value.length === 0) {
        displayValue = '(empty)';
      } else {
        displayValue = value.length > 3 
          ? `${value.slice(0, 3).join(', ')}... (${value.length} items)` 
          : value.join(', ');
      }
    } 
    else if (typeof value === 'object') {
      displayValue = '(object)';
    }
    else {
      // For string values, truncate if too long
      const strValue = String(value);
      displayValue = strValue.length > 50 ? strValue.substring(0, 47) + '...' : strValue;
    }
    
    return this.sanitizer.bypassSecurityTrustHtml(displayValue);
  }
  
  getCustomActions(entity: Entity): { key: string, label: string, icon?: string }[] {
    const customActions = this.entityAttributes.entityAttributes[this.entityType]?.customActions;
    if (!customActions) return [];
    
    // Filter actions based on conditions
    return Object.entries(customActions)
      .filter(([_, action]) => !action.condition || action.condition(entity))
      .map(([key, action]) => ({
        key,
        label: action.label,
        icon: action.icon
      }));
  }
  
  executeCustomAction(actionKey: string, entity: Entity): void {
    const action = this.entityAttributes.entityAttributes[this.entityType]?.customActions?.[actionKey];
    if (action) {
      action.action(entity);
    }
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