import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { EntityService, Entity, EntityMetadata } from '../../services/entity.service';
import { CommonModule } from '@angular/common';
import { ROUTE_CONFIG } from '../../constants';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { EntityAttributesService } from '../../services/entity-attributes.service';
import { EntityDisplayService } from '../../services/entity-display.service';

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
                <dd class="col-sm-9" [innerHTML]="entity ? formatFieldValue(entity, field) : ''"></dd>
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
    private entityAttributes: EntityAttributesService,
    private entityDisplay: EntityDisplayService,
    private route: ActivatedRoute,
    private router: Router,
    private sanitizer: DomSanitizer
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
    
    // Use only metadata to determine field visibility
    this.displayFields = Object.keys(this.metadata.fields).filter(field => {
      const fieldMeta = this.metadata?.fields[field];
      if (!fieldMeta) return false;
      
      // Use display service to check if field should be shown
      return this.entityDisplay.showInView(fieldMeta, 'details');
    });
    
    // Sort fields based on displayAfterField
    this.sortDisplayFields();
  }
  
  sortDisplayFields(): void {
    // We're ignoring displayAfterField sorting for now - doing nothing here
    // The fields will appear in the order they come from the data structure
  }
  
  // Local function to check if field should be shown in view - no longer needed
  /*
  localShowInView(fieldMetadata: any, view: string): boolean {
    const display = fieldMetadata.display || '';
    
    if (display === 'hidden') {
      return false;
    }
    
    return display === '' || display === 'all' || display.includes(view);
  }
  */

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
    
    // Use widget type for display formatting
    if (widget === 'password') {
      displayValue = '••••••••'; // Mask password
    }
    // Format based on field type
    else if (fieldType === 'ISODate' && typeof value === 'string') {
      const date = new Date(value);
      displayValue = isNaN(date.getTime()) ? value : date.toLocaleString();
    } 
    else if (fieldType === 'Boolean') {
      displayValue = value ? 'Yes' : 'No';
    } 
    else if (fieldType === 'ObjectId') {
      displayValue = String(value);
    } 
    else if (Array.isArray(value)) {
      if (value.length === 0) {
        displayValue = '(empty array)';
      } else {
        displayValue = value.join(', ');
      }
    } 
    else if (typeof value === 'object') {
      if (Object.keys(value).length === 0) {
        displayValue = '(empty object)';
      } else {
        try {
          displayValue = '<pre>' + JSON.stringify(value, null, 2) + '</pre>';
        } catch (e) {
          displayValue = String(value);
        }
      }
    }
    else {
      displayValue = String(value);
    }
    
    return this.sanitizer.bypassSecurityTrustHtml(displayValue);
  }

  goToEdit(): void {
    this.router.navigate([ROUTE_CONFIG.getEntityEditRoute(this.entityType, this.entityId)]);
  }

  goBack(): void {
    this.router.navigate([ROUTE_CONFIG.getEntityListRoute(this.entityType)]);
  }
}