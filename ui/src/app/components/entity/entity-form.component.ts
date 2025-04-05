import { Component, OnInit } from '@angular/core';
import { FormGroup, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { EntityService } from '../../services/entity.service';
import { MetadataService, Metadata } from '../../services/metadata.service';
import { FormGeneratorService } from '../../services/form-generator.service';
import { CommonModule } from '@angular/common';
// Removed constants import as constants.ts was removed

@Component({
  selector: 'app-entity-form',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  template: `
    <div class="container mt-4">
      <div class="d-flex justify-content-between align-items-center mb-4">
        <h2>{{ isEditMode ? 'Edit' : 'Create' }} {{ entityType | titlecase }}</h2>
        <button class="btn btn-secondary" (click)="goBack()">Back to List</button>
      </div>
      
      <div *ngIf="loading" class="text-center">
        <p>Loading...</p>
      </div>
      
      <div *ngIf="error" class="alert alert-danger">
        {{ error }}
      </div>
      
      <div *ngIf="!loading && !error && entityForm">
        <form [formGroup]="entityForm" (ngSubmit)="onSubmit()">
          <div class="card">
            <div class="card-body">
              <div class="row">
                <ng-container *ngFor="let fieldName of sortedFields">
                  <div class="col-md-6 mb-3">
                    <label [for]="fieldName" class="form-label">
                      {{ getFieldDisplayName(fieldName) }}
                      <span *ngIf="isFieldRequired(fieldName)" class="text-danger">*</span>
                    </label>
                    
                    <!-- Input field based on field type and widget -->
                    <span *ngIf="true">
                    <ng-container [ngSwitch]="getFieldWidget(fieldName)">
                      
                      <!-- Select dropdown -->
                      <select *ngSwitchCase="'select'" 
                        [id]="fieldName" 
                        [formControlName]="fieldName" 
                        class="form-select"
                        [class.is-invalid]="isFieldInvalid(fieldName)">
                        <option value="">Select {{ getFieldDisplayName(fieldName) }}</option>
                        <option *ngFor="let option of getFieldOptions(fieldName)" [value]="option">
                          {{ option }}
                        </option>
                      </select>
                      
                      <!-- Checkbox -->
                      <div *ngSwitchCase="'checkbox'" class="form-check mt-2">
                        <input type="checkbox" 
                          [id]="fieldName" 
                          [formControlName]="fieldName" 
                          class="form-check-input"
                          [class.is-invalid]="isFieldInvalid(fieldName)">
                        <label [for]="fieldName" class="form-check-label">
                          {{ getFieldDisplayName(fieldName) }}
                        </label>
                      </div>
                      
                      <!-- Textarea -->
                      <textarea *ngSwitchCase="'textarea'" 
                        [id]="fieldName" 
                        [formControlName]="fieldName" 
                        class="form-control"
                        [class.is-invalid]="isFieldInvalid(fieldName)"
                        rows="3"></textarea>
                      
                      <!-- Date input -->
                      <input *ngSwitchCase="'date'" 
                        type="datetime-local" 
                        [id]="fieldName" 
                        [formControlName]="fieldName" 
                        class="form-control"
                        [class.is-invalid]="isFieldInvalid(fieldName)">
                      
                      <!-- Password input -->
                      <input *ngSwitchCase="'password'" 
                        type="password" 
                        [id]="fieldName" 
                        [formControlName]="fieldName" 
                        class="form-control"
                        [class.is-invalid]="isFieldInvalid(fieldName)">
                        
                      <!-- Email input -->
                      <input *ngSwitchCase="'email'" 
                        type="email" 
                        [id]="fieldName" 
                        [formControlName]="fieldName" 
                        class="form-control"
                        [class.is-invalid]="isFieldInvalid(fieldName)">
                        
                      <!-- Reference input (for ObjectId fields) -->
                      <input *ngSwitchCase="'reference'" 
                        type="text" 
                        [id]="fieldName" 
                        [formControlName]="fieldName" 
                        class="form-control"
                        [class.is-invalid]="isFieldInvalid(fieldName)"
                        placeholder="Select or enter ID">
                      
                      <!-- JSON input -->
                      <textarea *ngSwitchCase="'json'" 
                        [id]="fieldName" 
                        [formControlName]="fieldName" 
                        class="form-control"
                        [class.is-invalid]="isFieldInvalid(fieldName)"
                        rows="3"
                        placeholder="{ }"></textarea>
                      
                      <!-- Array input -->
                      <textarea *ngSwitchCase="'array'" 
                        [id]="fieldName" 
                        [formControlName]="fieldName" 
                        class="form-control"
                        [class.is-invalid]="isFieldInvalid(fieldName)"
                        rows="3"
                        placeholder="[]"></textarea>
                      
                      <!-- Default text input -->
                      <input *ngSwitchDefault 
                        type="text" 
                        [id]="fieldName" 
                        [formControlName]="fieldName" 
                        class="form-control"
                        [class.is-invalid]="isFieldInvalid(fieldName)">
                    </ng-container>
                    </span>
                    
                    <!-- Validation error messages -->
                    <div *ngIf="isFieldInvalid(fieldName)" class="invalid-feedback">
                      <div *ngIf="entityForm && entityForm.get(fieldName)?.errors?.['required']">
                        {{ getFieldDisplayName(fieldName) }} is required.
                      </div>
                      <div *ngIf="entityForm && entityForm.get(fieldName)?.errors?.['minlength']">
                        {{ getFieldDisplayName(fieldName) }} must be at least 
                        {{ entityForm.get(fieldName)?.errors?.['minlength']?.requiredLength }} characters.
                      </div>
                      <div *ngIf="entityForm && entityForm.get(fieldName)?.errors?.['maxlength']">
                        {{ getFieldDisplayName(fieldName) }} cannot exceed 
                        {{ entityForm.get(fieldName)?.errors?.['maxlength']?.requiredLength }} characters.
                      </div>
                      <div *ngIf="entityForm && entityForm.get(fieldName)?.errors?.['pattern']">
                        {{ getFieldDisplayName(fieldName) }} has an invalid format.
                      </div>
                      <div *ngIf="entityForm && entityForm.get(fieldName)?.errors?.['min']">
                        {{ getFieldDisplayName(fieldName) }} must be at least 
                        {{ entityForm.get(fieldName)?.errors?.['min']?.min }}.
                      </div>
                      <div *ngIf="entityForm && entityForm.get(fieldName)?.errors?.['max']">
                        {{ getFieldDisplayName(fieldName) }} cannot exceed 
                        {{ entityForm.get(fieldName)?.errors?.['max']?.max }}.
                      </div>
                    </div>
                  </div>
                </ng-container>
              </div>
            </div>
            <div class="card-footer">
              <button type="submit" class="btn btn-primary" [disabled]="entityForm && entityForm.invalid || submitting">
                {{ submitting ? 'Saving...' : (isEditMode ? 'Update' : 'Create') }}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  `,
  styles: [`
    .container { max-width: 1000px; }
  `]
})
export class EntityFormComponent implements OnInit {
  entityType: string = '';
  entityId: string = '';
  isEditMode: boolean = false;
  
  data: any[] = [];
  metadata: Metadata | null = null;
  entityForm: FormGroup | null = null;
  sortedFields: string[] = [];
  entity: any = null; // Add missing entity property
  
  loading: boolean = true;
  submitting: boolean = false;
  error: string = '';

  constructor(
    private entityService: EntityService,
    private formGenerator: FormGeneratorService,
    private metadataService: MetadataService,
    private route: ActivatedRoute,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.route.params.subscribe(params => {
      this.entityType = params['entityType'];
      this.entityId = params['id'];
      this.isEditMode = this.route.snapshot.url.some(segment => segment.path === 'edit');
      
      if (this.isEditMode) {
        this.loadEntityForEdit();
      } else {
        this.loadMetadataForCreate();
      }
    });
  }

  loadMetadataForCreate(): void {
    this.loading = true;
    this.error = '';
    
    // Wait for entities to be loaded
    this.metadataService.waitForEntities()
      .then(() => {
        try {
          // Get metadata from AllEntitiesService
          this.metadata = this.metadataService.getEntityMetadata(this.entityType);
          this.initForm();
          this.loading = false;
        } catch (err) {
          console.error('Error loading metadata:', err);
          this.error = 'Failed to load form. Please try again later.';
          this.loading = false;
        }
      })
      .catch(error => {
        console.error('Error waiting for entities:', error);
        this.error = 'Failed to load entity metadata. Please refresh the page.';
        this.loading = false;
      });
  }

  loadEntityForEdit(): void {
    this.loading = true;
    this.error = '';
    
    // Wait for entities to be loaded
    this.metadataService.waitForEntities()
      .then(() => {
        try {
          // First get the metadata
          this.metadata = this.metadataService.getEntityMetadata(this.entityType);
          
          // Then load the entity data
          this.entityService.getEntity(this.entityType, this.entityId).subscribe({
        next: (response) => {
          // For a single entity, response.data will be a single object
          this.entity = response.data; // Set directly for form initialization
          this.data = response.data;   // Keep this.data for backward compatibility
          this.initForm();
          this.loading = false;
        },
        error: (err) => {
          console.error('Error loading entity for edit:', err);
          this.error = 'Failed to load entity data. Please try again later.';
          this.loading = false;
        }
      });
        } catch (err) {
          console.error('Error loading metadata:', err);
          this.error = 'Failed to load entity metadata. Please try again later.';
          this.loading = false;
        }
      })
      .catch(error => {
        console.error('Error waiting for entities:', error);
        this.error = 'Failed to load entity metadata. Please refresh the page.';
        this.loading = false;
      });
  }

  initForm(): void {
    if (!this.metadata) return;
    
    // Generate the form for the entity - convert null to undefined to match expected type
    this.entityForm = this.formGenerator.generateForm(this.metadata, this.entity || undefined);
    
    // Get the list of fields from the generated form
    if (this.entityForm) {
      this.sortedFields = Object.keys(this.metadata.fields).filter(field => {
        return this.entityForm?.get(field) !== null && this.entityForm?.get(field) !== undefined;
      });
    }
  }

  getFieldDisplayName(fieldName: string): string {
    if (!this.metadata) return fieldName;
    return this.metadata.fields[fieldName]?.ui?.displayName || fieldName;
  }

  getFieldWidget(fieldName: string): string {
    const fieldMeta = this.metadata?.fields[fieldName];
    if (!fieldMeta) return 'text';
    
    // If widget is explicitly specified in ui object, use it
    if (fieldMeta.ui?.widget) return fieldMeta.ui.widget;
    
    // Check if field has enum values - use select dropdown
    if (fieldMeta.enum && fieldMeta.enum.values && fieldMeta.enum.values.length > 0) {
      return 'select';
    }
    
    // Default widgets based on field type
    const fieldType = fieldMeta.type;
    switch (fieldType) {
      case 'Boolean':
        return 'checkbox';
      case 'ISODate':
        return 'date';
      case 'String':
        // Special string field types based on metadata patterns, not field names
        if (fieldMeta.pattern?.regex?.includes('@')) return 'email';
        if (fieldMeta.maxLength && fieldMeta.maxLength > 100) return 'textarea';
        return 'text';
      case 'ObjectId':
        return 'reference';
      case 'Array':
      case 'Array[String]':
        return 'array';
      case 'JSON':
        return 'json';
      default:
        return 'text';
    }
  }


  getFieldOptions(fieldName: string): string[] {
    if (!this.metadata) return [];
    const fieldMeta = this.metadata.fields[fieldName];
    if (!fieldMeta || !fieldMeta.enum || !fieldMeta.enum.values) return [];
    
    return fieldMeta.enum.values;
  }

  isFieldRequired(fieldName: string): boolean {
    if (!this.metadata) return false;
    const fieldMeta = this.metadata.fields[fieldName];
    if (!fieldMeta) return false;
    
    // Field required property is at the root level, not in the UI object
    return fieldMeta['required'] || false;
  }

  isFieldInvalid(fieldName: string): boolean {
    if (!this.entityForm) return false;
    const control = this.entityForm.get(fieldName);
    return !!control && control.invalid && (control.dirty || control.touched);
  }

  onSubmit(): void {
    if (!this.entityForm || this.entityForm.invalid) return;
    
    this.submitting = true;
    let formData = this.entityForm.value;
    
    // Process the form data before sending it to the API
    formData = this.processFormData(formData);
    
    if (this.isEditMode) {
      this.updateEntity(formData);
    } else {
      this.createEntity(formData);
    }
  }
  
  // Process form data before submitting to the API
  processFormData(formData: any): any {
    // Clone the data to avoid modifying the form values directly
    const processedData = { ...formData };
    
    try {
      // Get all available fields for the form view using metadataService
      const formFields = this.metadataService.getViewFields(this.entityType, 'form');
      
      // Handle autoGenerate and autoUpdate fields
      formFields.forEach(fieldName => {
        try {
          // Get field metadata using metadataService
          const fieldMeta = this.metadataService.getFieldMetadata(this.entityType, fieldName);
          
          // Handle ISODate fields that need auto-generation
          if (fieldMeta.type === 'ISODate') {
            // For create operations, handle autoGenerate fields
            if (!this.isEditMode && fieldMeta.autoGenerate) {
              processedData[fieldName] = new Date().toISOString();
              console.log(`Auto-generated date for ${fieldName}: ${processedData[fieldName]}`);
            }
            
            // For both create and edit operations, handle autoUpdate fields
            if (fieldMeta.autoUpdate) {
              processedData[fieldName] = new Date().toISOString();
              console.log(`Auto-updated date for ${fieldName}: ${processedData[fieldName]}`);
            }
          }
        } catch (error) {
          // Handle case where field metadata can't be found
          console.warn(`Could not get metadata for field: ${fieldName}`, error);
        }
      });
    } catch (error) {
      console.error('Error processing form data:', error);
    }
    
    return processedData;
  }

  createEntity(formData: any): void {
    this.entityService.createEntity(this.entityType, formData).subscribe({
      next: (response) => {
        this.submitting = false;
        // For now, just go back to the entity list to avoid navigation issues
        this.router.navigate(['/entity', this.entityType]);
      },
      error: (err) => {
        console.error('Error creating entity:', err);
        this.error = 'Failed to create entity. Please check your data and try again.';
        this.submitting = false;
      }
    });
  }

  updateEntity(formData: any): void {
    this.entityService.updateEntity(this.entityType, this.entityId, formData).subscribe({
      next: (response) => {
        this.submitting = false;
        // For now, just go back to the entity list to avoid navigation issues
        this.router.navigate(['/entity', this.entityType]);
      },
      error: (err) => {
        console.error('Error updating entity:', err);
        this.error = 'Failed to update entity. Please check your data and try again.';
        this.submitting = false;
      }
    });
  }

  goBack(): void {
    if (this.isEditMode && this.entityId) {
      this.router.navigate(['/entity', this.entityType, this.entityId]);
    } else {
      this.router.navigate(['/entity', this.entityType]);
    }
  }
}