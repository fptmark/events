import { Component, OnInit } from '@angular/core';
import { FormGroup, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { EntityService } from '../../services/entity.service';
import { MetadataService, EntityMetadata } from '../../services/metadata.service';
import { FormGeneratorService, FormMode, VIEW, CREATE, EDIT } from '../../services/form-generator.service';
import { CommonModule } from '@angular/common';
import { RestService } from '../../services/rest.service';

@Component({
  selector: 'app-entity-form',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  providers: [RestService],
  template: `
    <div class="container mt-4">
      <div class="d-flex justify-content-between align-items-center mb-4">
        <h2>{{ mode }} {{ entityType | titlecase }}</h2>
        <button class="btn btn-secondary" (click)="goBack()">Back</button>
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
                    
                    <!-- All form controls using formControlName automatically handle disabled state -->
                    <!-- Disabled controls will have their values populated by populateFormValues -->
                    <!-- So we can use the same controls for all states (view/edit/create) -->
                    <ng-container [ngSwitch]="formGenerator.getFieldWidget(entityType, fieldName, mode)">
                      
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

          <div class="card-footer d-flex justify-content-between">
            <!-- Left side (for view mode) -->
            <div>
              <ng-container *ngIf="isViewMode()">
                <div *ngIf="entityService.canUpdate(entityType)">
                  <button type="button" class="btn btn-primary me-2" (click)="goToEdit()">Edit</button>
                </div>
                <div *ngIf="entityService.canDelete(entityType)">
                  <button type="button" class="btn btn-danger" (click)="restService.deleteEntity(entityType, entityId)">Delete</button>
                </div>
              </ng-container>
            </div>

            <!-- Right side (for edit/create mode) -->
            <div>
              <ng-container *ngIf="!isViewMode()">
                <button type="submit" class="btn btn-primary" [disabled]="entityForm && entityForm.invalid || submitting">
                  {{ submitting ? 'Saving...' : 'Submit' }}
                </button>
                <button type="button" class="btn btn-secondary ms-2" (click)="goBack()">Cancel</button>
              </ng-container>
            </div>
          </div>
          </div>
        </form>
      </div>
    </div>
  `,
  styles: [`
    .container { max-width: 1000px; }
    
    /* Style for disabled (read-only) form controls */
    .form-control:disabled,
    .form-select:disabled,
    .form-check-input:disabled {
      background-color: #f8f9fa; /* Light gray background */
      color: #212529; /* Dark text for readability */
      opacity: 1; /* Full opacity for better readability */
      cursor: default;
      border: 1px solid #dee2e6;
    }
  `]
})

export class EntityFormComponent implements OnInit {
  readonly ID_FIELD = '_id'; // Changed from private to public

  entityType: string = '';
  entityId: string = '';
  
  data: any[] = [];
  entityMetadata: EntityMetadata | null = null;
  entityForm: FormGroup | null = null;
  sortedFields: string[] = [];
  entity: any = null;
  
  loading: boolean = true;
  submitting: boolean = false;
  error: string = '';

  mode: FormMode = VIEW;
  
  constructor(
    private route: ActivatedRoute,
    private router: Router,
    public entityService: EntityService,
    private metadataService: MetadataService,
    public formGenerator: FormGeneratorService,
    public restService: RestService
  ) {}
  
  // Helper methods for template conditions
  isViewMode(): boolean {
    return this.mode === VIEW;
  }
  
  isEditMode(): boolean {
    return this.mode === EDIT;
  }
  
  isCreateMode(): boolean {
    return this.mode === CREATE;
  }

  ngOnInit(): void {
    // Simplified initialization
    this.route.params.subscribe(params => {
      this.entityType = params['entityType'];
      this.entityId = params['id'];
      
      const url = this.router.url;
      
      if (url.includes('/create')) {
        this.mode = CREATE;
      } else if (url.includes('/edit')) {
        this.mode = EDIT;
      } else {
        this.mode = VIEW;
      }
      
      this.loadEntity();
    });
  }

  loadEntity(): void {
    this.loading = true;
    this.error = '';
    
    // Generate the form first (same for all modes)
    const result = this.formGenerator.generateEntityForm(this.entityType, this.mode);
    this.entityForm = result.form;
    this.sortedFields = result.displayFields;
    
    // For create mode, just populate with defaults and we're done
    if (this.isCreateMode()) {
      this.populateFormValues();
      this.loading = false;
      return;
    }
    
    // For edit/view mode, fetch the data first, then populate
    this.restService.getEntity(this.entityType, this.entityId).subscribe({
      next: (response) => {
        this.entity = response.data || response;
        
        if (!this.entity) {
          this.error = 'No entity data returned from the server.';
          this.loading = false;
          return;
        }
        
        // Populate form with entity data for edit/view mode
        this.populateFormValues(this.entity);
        this.loading = false;
      },
      error: (err) => {
        console.error('Error loading entity:', err);
        this.error = 'Failed to load entity data. Please try again later.';
        this.loading = false;
      }
    });
  }

  // initForm method removed - logic moved directly into loadMetadataForCreate and loadEntityForEdit

  getFieldDisplayName(fieldName: string): string {
    if (fieldName === this.ID_FIELD) return 'ID';
    const fieldMeta = this.metadataService.getFieldMetadata(this.entityType, fieldName);
    return fieldMeta?.ui?.displayName || fieldName;
  }



  getFieldOptions(fieldName: string): string[] {
    const fieldMeta = this.metadataService.getFieldMetadata(this.entityType, fieldName);
    if (!fieldMeta || !fieldMeta.enum || !fieldMeta.enum.values) return [];
    
    return fieldMeta.enum.values;
  }

  isFieldRequired(fieldName: string): boolean {
    if (fieldName === this.ID_FIELD) return true;
    
    const fieldMeta = this.metadataService.getFieldMetadata(this.entityType, fieldName);
    if (!fieldMeta) return false;
    
    // Field required property is at the root level, not in the UI object
    return fieldMeta.required || false;
  }

  isFieldInvalid(fieldName: string): boolean {
    if (!this.entityForm) return false;
    const control = this.entityForm.get(fieldName);
    return !!control && control.invalid && (control.dirty || control.touched);
  }
  
  isFieldReadOnly(fieldName: string): boolean {
    if (!this.entityForm) return false;
    const control = this.entityForm.get(fieldName);
    return control?.disabled || false;
  }
  
  
  /**
   * Populates form values based on mode and entity data
   * @param entityData Optional entity data for edit/view modes
   */
  populateFormValues(entityData?: any): void {
    if (!this.entityForm || !this.sortedFields.length) return;
    
    // Process each field
    for (const fieldName of this.sortedFields) {
      const control = this.entityForm.get(fieldName);
      if (!control) continue;
      
      // Get field metadata
      const fieldMeta = this.metadataService.getFieldMetadata(this.entityType, fieldName);
      
      // Get the value based on mode
      let value;
      
      if (this.isCreateMode()) {
        // Use default values for create mode
        value = this.getDefaultValue(fieldMeta);
        
        // Handle special types that need specific default values
        if (fieldMeta?.type === 'ISODate' && (fieldMeta?.autoGenerate || fieldMeta?.autoUpdate)) {
          // For auto-generate/update fields in create mode, use current date
          value = new Date().toISOString().substring(0, 16); // Format for datetime-local
        }
      } else {
        // Use entity data for edit/view modes
        value = entityData?.[fieldName];
        
        // Handle ISODate fields specially
        if (fieldMeta?.type === 'ISODate') {
          if (!value) {
            // For empty dates, ensure we display them properly as completely empty
            value = null; // Use null instead of empty string for date fields
          } else if (value) {
            try {
              // Format valid date strings
              if (typeof value === 'string' && value.match(/^\d{4}-\d{2}-\d{2}T/)) {
                // For input[type=datetime-local], format as YYYY-MM-DDThh:mm
                const date = new Date(value);
                value = date.toISOString().substring(0, 16); // Format for datetime-local input
              }
            } catch (e) {
              console.error('Error formatting date:', e);
            }
          }
          
          // For auto-update fields in edit mode, use current date
          if (this.isEditMode() && fieldMeta?.autoUpdate) {
            value = new Date().toISOString().substring(0, 16);
          }
        }
      }
      
      // Set value (disabled state is already handled by form generator)
      control.setValue(value);
    }
  }

  private getDefaultValue(fieldMeta: any): any {
    const type = fieldMeta.type;
    const widget = fieldMeta.ui?.widget || fieldMeta.widget;
    const enumValues = fieldMeta.enum?.values;
    const required = fieldMeta.required;
    
    switch (type) {
      case 'String':
        // For select fields with enum values, default to first value if required
        if (widget === 'select' && enumValues?.length > 0 && required) {
          return enumValues[0];
        }
        return '';
      case 'Number':
      case 'Integer':
        return required ? 0 : null;
      case 'Boolean':
        return false;
      case 'Array':
      case 'Array[String]':
        return [];
      case 'JSON':
        return {};
      case 'ISODate':
        // Always set current date for autoGenerate and autoUpdate fields
        if (fieldMeta.autoGenerate || fieldMeta.autoUpdate) {
          const now = new Date().toISOString();
          return now;
        }
        return null;
      case 'ObjectId':
        return '';
      default:
        return null;
    }
  }

  onSubmit(): void {
    if (!this.entityForm || this.entityForm.invalid) return;
    
    // For view mode, go to edit instead of submitting
    if (this.isViewMode()) {
      this.goToEdit();
      return;
    }
    
    this.submitting = true;
    let formData = this.entityForm.value;
    
    // Process the form data before sending it to the API
    formData = this.processFormData(formData);
    
    if (this.isEditMode()) {
      this.updateEntity(formData);
    } else if (this.isCreateMode()) {
      this.createEntity(formData);
    }
  }
  
  // Process form data before submitting to the API
  processFormData(formData: any): any {
    // Clone the data to avoid modifying the form values directly
    const processedData = { ...formData };
    
    try {
      if (!this.entityForm) return processedData;
      
      // Process all form controls directly (including disabled fields)
      for (const fieldName in this.entityForm.controls) {
        const control = this.entityForm.controls[fieldName];
        const fieldMeta = this.metadataService.getFieldMetadata(this.entityType, fieldName);
        
        if (control.disabled) {
          // Add disabled field values to the processed data (they're excluded from formData by default)
          const value = control.value;
          if (value !== undefined && value !== null) {
            processedData[fieldName] = value;
          }
        }
        
        // Special handling for specific field types
        if (fieldMeta && fieldMeta.type === 'ISODate') {
          const currentTime = new Date().toISOString();
          
          // For create operations, handle autoGenerate fields
          if (this.isCreateMode() && fieldMeta.autoGenerate) {
            processedData[fieldName] = currentTime;
          }
          
          // For both create and edit operations, always update autoUpdate fields
          if (fieldMeta.autoUpdate) {
            processedData[fieldName] = currentTime;
          }
        }
      }
    } catch (error) {
      console.error('Error processing form data:', error);
    }
    
    return processedData;
  }

  createEntity(formData: any): void {
    this.restService.createEntity(this.entityType, formData).subscribe({
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
    this.restService.updateEntity(this.entityType, this.entityId, formData).subscribe({
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
    if (this.isEditMode() && this.entityId) {
      this.router.navigate(['/entity', this.entityType, this.entityId]);
    } else {
      this.router.navigate(['/entity', this.entityType]);
    }
  }
  
  goToEdit(): void {
    if (this.entityId) {
      this.router.navigate(['/entity', this.entityType, this.entityId, 'edit']);
    }
  }
  
}