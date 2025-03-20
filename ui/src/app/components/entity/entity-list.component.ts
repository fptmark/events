import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { EntityService, Entity, EntityMetadata } from '../../services/entity.service';
import { CommonModule } from '@angular/common';
import { ROUTE_CONFIG } from '../../constants';
import { EntityAttributesService } from '../../services/entity-attributes.service';

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
              <td *ngFor="let field of displayFields">{{ formatFieldValue(entity, field) }}</td>
              <td>
                <ng-container *ngIf="isValidOperation(entityType, 'r')">
                  <button class="btn btn-sm btn-info me-2" (click)="viewEntity(entity._id)">View</button>
                </ng-container>
                <ng-container *ngIf="isValidOperation(entityType, 'u')">
                  <button class="btn btn-sm btn-warning me-2" (click)="editEntity(entity._id)">Edit</button>
                </ng-container>
                <ng-container *ngIf="isValidOperation(entityType, 'd')">
                  <button class="btn btn-sm btn-danger" (click)="deleteEntity(entity._id)">Delete</button>
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
    private route: ActivatedRoute,
    private router: Router
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
    if (!this.metadata) return;
    
    // First get fields that should be displayed in the list view
    const filteredFields = Object.keys(this.metadata.fields)
      .filter(field => {
        const fieldMeta = this.metadata?.fields[field];
        // Skip fields that are form-only or system fields
        if (!fieldMeta || fieldMeta.display === 'form') return false;
        if (['_id', 'createdAt', 'updatedAt'].includes(field) && this.displayFields.length > 3) return false;
        if (field === 'password') return false; // Never show password in list
        return true;
      });
    
    // Now sort them based on displayAfterField to maintain correct order
    // Build adjacency lists for topological sort
    const adjacencyMap = new Map<string, string[]>();
    
    // Initialize with empty arrays
    filteredFields.forEach(field => {
      adjacencyMap.set(field, []);
    });
    
    // Add edges
    filteredFields.forEach(field => {
      const afterField = this.metadata?.fields[field]?.displayAfterField;
      if (afterField && filteredFields.includes(afterField)) {
        adjacencyMap.get(afterField)?.push(field);
      }
    });
    
    // Find root nodes (fields that don't come after any other field)
    const rootFields = filteredFields.filter(field => {
      return !filteredFields.some(otherField => 
        this.metadata?.fields[field]?.displayAfterField === otherField
      );
    });
    
    // Perform topological sort
    const visited = new Set<string>();
    const sortedFields: string[] = [];
    
    const visit = (field: string) => {
      if (visited.has(field)) return;
      visited.add(field);
      
      const nextFields = adjacencyMap.get(field) || [];
      nextFields.forEach(nextField => visit(nextField));
      
      sortedFields.push(field);
    };
    
    rootFields.forEach(field => visit(field));
    
    // Use the sorted fields, limiting to prevent overcrowding
    this.displayFields = sortedFields.slice(0, 6);
    
    // If no fields were found, fall back to default behavior
    if (this.displayFields.length === 0) {
      this.displayFields = filteredFields.slice(0, 6);
    }
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
    
    // Password field handling
    if (fieldName === 'password' || widget === 'password') {
      return '••••••••'; // Mask password
    }
    
    // Format based on field type
    if (fieldType === 'ISODate' && typeof value === 'string') {
      const date = new Date(value);
      return isNaN(date.getTime()) ? value : date.toLocaleString();
    } else if (fieldType === 'Boolean') {
      return value ? 'Yes' : 'No';
    } else if (fieldType === 'ObjectId') {
      // Truncate long IDs for better display
      const strValue = String(value);
      return strValue.length > 10 ? strValue.substring(0, 7) + '...' : strValue;
    } else if (Array.isArray(value)) {
      if (value.length === 0) return '(empty)';
      return value.length > 3 
        ? `${value.slice(0, 3).join(', ')}... (${value.length} items)` 
        : value.join(', ');
    } else if (typeof value === 'object') {
      return '(object)';
    }
    
    // For string values, truncate if too long
    const strValue = String(value);
    return strValue.length > 50 ? strValue.substring(0, 47) + '...' : strValue;
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