import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { MetadataService } from '../../services/metadata.service';
import { CommonModule, NgIf, NgFor } from '@angular/common';
import { EntityService } from '../../services/entity.service';
// // Removed constants import as constants.ts was removed

@Component({
  selector: 'app-entity-detail',
  standalone: true,
  imports: [CommonModule, NgIf, NgFor],
  template: `
    <div class="container mt-4">
      <div class="d-flex justify-content-between align-items-center mb-4">
        <h2>{{ metadataService.getTitle(entityType) }} Details</h2>
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
      
      <div *ngIf="!loading && !error && data">
        <div class="card mb-4">
          <div class="card-body">
            <dl class="row">
              <ng-container *ngFor="let field of displayFields">
                <dt class="col-sm-3">{{ metadataService.getFieldDisplayName(entityType, field) }}</dt>
                <dd class="col-sm-9" [innerHTML]="metadataService.formatFieldValue(entityType, field, 'details', data[field])">
                </dd>
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
  data: any = null;
  displayFields: string[] = [];
  loading: boolean = true;
  error: string = '';

  constructor(
    private entityService: EntityService,
    public metadataService: MetadataService,
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
    this.metadataService.waitForEntities()
      .then(() => {
        // First get the fields to display from metadata for 'details' view
        try {
          this.displayFields = this.metadataService.getViewFields(this.entityType, 'details');
          console.log('Display fields for details view:', this.displayFields);
          
          if (this.displayFields.length === 0) {
            throw new Error(`No fields configured for 'details' view of entity type: ${this.entityType}`);
          }
          
          // Then load entity data using the entity service
          this.entityService.getEntity(this.entityType, this.entityId).subscribe({
            next: (response) => {
              // The API returns the entity directly
              this.data = response;
              this.loading = false;
              
              console.log('Entity data loaded:', this.data);
            },
            error: (err) => {
              console.error('Error loading entity:', err);
              this.error = 'Failed to load entity details. Please try again later.';
              this.loading = false;
            }
          });
        } catch (error) {
          console.error('Error getting view fields:', error);
          this.error = `Failed to get field configuration: ${error}`;
          this.loading = false;
        }
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
    return this.metadataService.isValidOperation(this.entityType, operation);
  }
}