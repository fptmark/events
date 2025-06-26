import { Component, OnInit, OnDestroy } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { MetadataService } from '../services/metadata.service';
import { EntityService } from '../services/entity.service';
import { ConfigService } from '../services/config.service';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { RestService } from '../services/rest.service';
import { ModeService, SUMMARY } from '../services/mode.service';
import { forkJoin, of } from 'rxjs';
import { map, switchMap } from 'rxjs/operators';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { NotificationService } from '../services/notification.service';
import { ValidationService } from '../services/validation.service';
import { RefreshService } from '../services/refresh.service';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-entity-list',
  standalone: true,
  imports: [CommonModule],
  styleUrls: ['../common.css'],
  template: `
    <div class="container-fluid mt-4">
      <h2>{{ metadataService.getTitle(entityType) }}</h2>
      
      <!-- Create button - permission checked once per page -->
      <div *ngIf="metadataService.isValidOperation(entityType, 'c')">
        <div class="mb-3">
          <button class="btn btn-entity-create" (click)="this.entityService.navigateToCreate(entityType)">Create {{ entityType }}</button>
        </div>
      </div>
      
      <div *ngIf="loading" class="text-center">
        <p>Loading...</p>
      </div>
      
      <div *ngIf="error" class="alert alert-danger">
        {{ error }}
      </div>
      
      <div *ngIf="!loading && !error">
        <!-- Check if there are any entities to display -->
        <div *ngIf="data.length === 0" class="alert alert-info">
          No {{ entityType }} records found.
        </div>
        
        <!-- Table layout with one row per entity -->
        <div *ngIf="data.length > 0" class="table-responsive">
          <table class="table table-striped table-hover">
            <thead>
              <tr>
                <th *ngFor="let field of displayFields">{{ entityService.getFieldDisplayName(entityType, field) }}</th>
                <th class="actions-column">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr *ngFor="let row of data">
                <td *ngFor="let field of displayFields" [innerHTML]="row._formattedValues?.[field] | async"></td>
                <td class="actions-column text-nowrap">
                  <div class="btn-group btn-group-sm">
                    <!-- Consistent button order: View, Edit, Create, Delete -->
                    <button *ngIf="entityService.canRead(entityType)"
                      class="btn btn-entity-details me-1"
                      (click)="this.entityService.viewEntity(entityType, row['id'])">Details</button>
                    <button *ngIf="entityService.canUpdate(entityType)"
                      class="btn btn-entity-edit me-1"
                      (click)="this.entityService.editEntity(entityType, row['id'])">Edit</button>
                    <!-- Create not shown for individual rows since it applies to the entity type, not a specific row -->
                    <button *ngIf="entityService.canDelete(entityType)"
                      class="btn btn-entity-delete"
                      (click)="this.restService.deleteEntity(entityType, row['id'])">Delete</button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .container-fluid { 
      padding-left: 10px;
      padding-right: 10px;
    }
    
    /* Make table fill available space */
    .table-responsive {
      width: 100%;
      overflow-x: auto;
      margin-bottom: 20px; /* Add space below table */
      padding-bottom: 5px; /* Ensure bottom of table is visible */
    }
    
    /* Use auto table layout for more natural column sizing */
    .table {
      width: 100%;
      table-layout: auto;
    }
    
    /* Fix action buttons visibility */
    .btn-group {
      white-space: nowrap;
      display: flex;
    }
    
    /* Ensure text truncation starts at beginning, not end */
    td {
      max-width: 300px; /* Larger max-width for data cells */
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      direction: rtl;  /* Right-to-left to truncate start of text */
      text-align: left; /* Keep text aligned left */
    }
    
    /* Actions column should not truncate and should have enough space */
    .actions-column {
      direction: ltr;
      white-space: nowrap;
      width: 200px !important; /* Force minimum width with !important */
      min-width: 200px !important;
      padding-right: 15px !important; /* Add some extra padding */
    }
    
    /* Ensure headers match cell widths */
    th {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  `]
})
export class EntityListComponent implements OnInit, OnDestroy {
  entityType: string = '';
  data: any[] = []
  displayFields: string[] = [];
  loading: boolean = true;
  error: string = '';
  totalCount: number = 0;
  
  // Store operation permissions for row-level actions
  canRead: boolean = false;
  canUpdate: boolean = false;
  canDelete: boolean = false;
  
  // Refresh subscription
  private refreshSubscription: Subscription | null = null;

  constructor(
    public metadataService: MetadataService,
    public entityService: EntityService,
    private route: ActivatedRoute,
    public restService: RestService,
    private modeService: ModeService,
    private sanitizer: DomSanitizer,
    private notificationService: NotificationService,
    private validationService: ValidationService,
    private refreshService: RefreshService
  ) {}

  ngOnInit(): void {
    this.route.params.subscribe(params => {
      this.entityType = params['entityType'];
      
      // Clean up previous refresh subscription
      if (this.refreshSubscription) {
        this.refreshSubscription.unsubscribe();
      }
      
      // Subscribe to refresh events for this entity type
      this.refreshSubscription = this.refreshService.getRefreshObservable(this.entityType).subscribe(() => {
        console.log(`EntityListComponent: Refresh triggered for ${this.entityType}`);
        this.loadEntities();
      });
      
      // Load entities
      this.loadEntities();
    });
  }
  
  loadEntities(): void {
    this.loading = true;
    this.error = '';
    
    // Wait for entities to be loaded
    this.displayFields = this.entityService.getViewFields(this.entityType, SUMMARY);
        
    // Use RestService instead of HttpClient directly  
    this.restService.getEntityList(this.entityType, 'summary').subscribe({
      next: (response: any) => {
        // Handle new response format with metadata
        const entities = response.data || response; // Fallback for old format
        this.totalCount = response.metadata?.total || entities.length; // Extract count
        
        // Update the entity service with the current record count
        this.entityService.setRecordCount(this.totalCount);
        
        // Process each entity using embedded FK data from server response
        this.data = entities.map((entity: any) => {
          const processedEntity: any = { ...entity, _formattedValues: {} };

          this.displayFields.forEach(field => {
            const metadata = this.metadataService.getFieldMetadata(this.entityType, field);
            const rawValue = entity[field];

            // Check if it's an ObjectId field with a show configuration for the current mode (SUMMARY)
            const showConfig = metadata?.ui?.show ? this.metadataService.getShowConfig(this.entityType, field, SUMMARY) : null;

            if (metadata?.type === 'ObjectId' && showConfig) {
              // Use embedded FK data instead of making individual REST calls
              const formattedValue = this.entityService.formatObjectIdValueWithEmbeddedData(
                this.entityType, field, SUMMARY, rawValue, entity, showConfig
              );
              processedEntity._formattedValues[field] = of(this.sanitizer.bypassSecurityTrustHtml(formattedValue));
            } else {
              // For other field types or ObjectId without show config, use the synchronous formatter
              const formattedValue = this.entityService.formatFieldValue(this.entityType, field, SUMMARY, rawValue);
              processedEntity._formattedValues[field] = of(this.sanitizer.bypassSecurityTrustHtml(formattedValue));
            }
          });

          return processedEntity;
        });
            
        this.loading = false;
      },
      error: (err) => {
        console.error('Error loading entities:', err);
        this.error = 'Failed to load entities';
        this.loading = false;
      }
    });
  }
  
  // Custom actions are not currently implemented in the stateless approach
  // getCustomActions(entity: Entity): { key: string, label: string, icon?: string }[] {
  //   // Will be implemented when hooks are added back
  //   return [];
  // }
  
  // executeCustomAction(actionKey: string, entity: Entity): void {
  //   // Will be implemented when hooks are added back
  //   console.log(`Custom action ${actionKey} would be executed on entity:`, entity);
  // }

  ngOnDestroy(): void {
    // Clean up refresh subscription
    if (this.refreshSubscription) {
      this.refreshSubscription.unsubscribe();
    }
  }
  
}