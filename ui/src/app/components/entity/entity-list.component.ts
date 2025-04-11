import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { MetadataService } from '../../services/metadata.service';
import { EntityService } from '../../services/entity.service';
import { ConfigService } from '../../services/config.service';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { RestService } from '../../services/rest.service';

@Component({
  selector: 'app-entity-list',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="container mt-4">
      <h2>{{ metadataService.getTitle(entityType) }}</h2>
      
      <!-- Create button - permission checked once per page -->
      <div *ngIf="metadataService.isValidOperation(entityType, 'c')">
        <div class="mb-3">
          <button class="btn btn-primary" (click)="this.entityService.navigateToCreate(entityType)">Create {{ entityType }}</button>
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
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr *ngFor="let row of data">
                <td *ngFor="let field of displayFields" [innerHTML]="entityService.formatFieldValue(entityType, field, 'summary', row[field])"></td>
                <td>
                  <div class="btn-group btn-group-sm">
                    <button *ngIf="canRead" 
                      class="btn btn-info me-1" 
                      (click)="this.entityService.viewEntity(entityType, row['_id'])">View</button>
                    <button *ngIf="canUpdate" 
                      class="btn btn-warning me-1" 
                      (click)="this.entityService.editEntity(entityType, row['_id'])">Edit</button>
                    <button *ngIf="canDelete" 
                      class="btn btn-danger" 
                      (click)="this.restService.deleteEntity(entityType, row._id, loadEntities.bind(this))">Delete</button>
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
    .container { max-width: 1200px; }
  `]
})
export class EntityListComponent implements OnInit {
  entityType: string = '';
  data: any[] = []
  displayFields: string[] = [];
  loading: boolean = true;
  error: string = '';
  
  // Store operation permissions for row-level actions
  canRead: boolean = false;
  canUpdate: boolean = false;
  canDelete: boolean = false;

  constructor(
    public metadataService: MetadataService,
    public entityService: EntityService,
    private route: ActivatedRoute,
    public restService: RestService,
    private configService: ConfigService,
    private http: HttpClient
  ) {}

  ngOnInit(): void {
    this.route.params.subscribe(params => {
      this.entityType = params['entityType'];
      
      // Initialize permissions for this entity type
      this.initializePermissions();
      
      // Load entities
      this.loadEntities();
    });
  }
  
  initializePermissions(): void {
    // Check row-level operation permissions once
    this.canRead = this.metadataService.isValidOperation(this.entityType, 'r');
    this.canUpdate = this.metadataService.isValidOperation(this.entityType, 'u');
    this.canDelete = this.metadataService.isValidOperation(this.entityType, 'd');
  }

  loadEntities(): void {
    this.loading = true;
    this.error = '';
    
    // Wait for entities to be loaded
    this.displayFields = this.entityService.getViewFields(this.entityType, 'summary');
        
    // Get API endpoint from config service
    const apiUrl = this.configService.getApiUrl(this.entityType);
        
    // Now fetch the entity data from the API
    this.http.get<any>(apiUrl).subscribe({
      next: (response) => {
        this.data = Array.isArray(response) ? response : [response];
            
          this.loading = false;
        },
        error: (err) => {
          console.error('Error loading entities:', err);
          this.error = 'Failed to load entities. Please try again later.';
          this.loading = false;
        }
      })
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

  
}