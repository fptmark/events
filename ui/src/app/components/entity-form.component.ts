import { Component, OnInit } from '@angular/core';
import { FormGroup, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { EntityService } from '../services/entity.service';
import { MetadataService, EntityMetadata } from '../services/metadata.service';
import { FormGeneratorService } from '../services/form-generator.service';
import { CommonModule } from '@angular/common';
import { RestService } from '../services/rest.service';
import { ViewService, ViewMode, VIEW, EDIT, CREATE } from '../services/view.service';
import { NavigationService } from '../services/navigation.service';
import { ValidationError, ErrorResponse } from '../services/rest.service';

@Component({
  selector: 'app-entity-form',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  providers: [RestService],
  template: `
    <div class="container-fluid mt-4">
      <div class="d-flex justify-content-between align-items-center mb-4">
        <h2>{{ mode }} {{ entityType | titlecase }}</h2>
        <button class="btn btn-secondary" (click)="goBack()">Back</button>
      </div>
      
      <div *ngIf="error" class="alert alert-danger" style="white-space: pre-wrap;">
        {{ error }}
      </div>
      
      <div *ngIf="!error && entityForm">
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
                    <ng-container [ngSwitch]="formGenerator.getFieldAttributes(entityType, fieldName, mode).fieldType">
                      
                      <!-- Select dropdown -->
                      <select *ngSwitchCase="'select'" 
                        [id]="fieldName" 
                        [formControlName]="fieldName" 
                        class="form-select"
                        [class.is-invalid]="isFieldInvalid(fieldName) || getFieldValidationError(fieldName) !== null">
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
                          [class.is-invalid]="isFieldInvalid(fieldName) || getFieldValidationError(fieldName) !== null">
                        <label [for]="fieldName" class="form-check-label">
                          {{ getFieldDisplayName(fieldName) }}
                        </label>
                      </div>
                      
                      <!-- Textarea -->
                      <textarea *ngSwitchCase="'textarea'" 
                        [id]="fieldName" 
                        [formControlName]="fieldName" 
                        class="form-control"
                        [class.is-invalid]="isFieldInvalid(fieldName) || getFieldValidationError(fieldName) !== null"
                        rows="3"></textarea>
                      
                      <!-- Date input -->
                      <input *ngSwitchCase="'date'" 
                        type="date" 
                        [id]="fieldName" 
                        [formControlName]="fieldName" 
                        class="form-control"
                        [class.is-invalid]="isFieldInvalid(fieldName) || getFieldValidationError(fieldName) !== null">
                      
                      <!-- Password input -->
                      <input *ngSwitchCase="'password'" 
                        type="password" 
                        [id]="fieldName" 
                        [formControlName]="fieldName" 
                        class="form-control"
                        [class.is-invalid]="isFieldInvalid(fieldName) || getFieldValidationError(fieldName) !== null">
                        
                      <!-- Email input -->
                      <input *ngSwitchCase="'email'" 
                        type="email" 
                        [id]="fieldName" 
                        [formControlName]="fieldName" 
                        class="form-control"
                        [class.is-invalid]="isFieldInvalid(fieldName) || getFieldValidationError(fieldName) !== null">
                        
                      <!-- ObjectId input -->
                      <div *ngSwitchCase="'ObjectId'" class="input-group">
                        <input
                          type="text" 
                          [id]="fieldName" 
                          [formControlName]="fieldName" 
                          [class.link-input]="!isEditMode()"
                          class="form-control"
                          [class.is-invalid]="isFieldInvalid(fieldName) || getFieldValidationError(fieldName) !== null"
                          (click)="openLink(fieldName)"
                          placeholder="{{ isEditMode() ? 'Click to select ID or enter manually' : 'Click to view entity' }}">
                        <button *ngIf="isEditMode()" 
                          class="btn btn-outline-secondary" 
                          type="button"
                          (click)="openLink(fieldName)">
                          Select
                        </button>
                      </div>
                      
                      <!-- JSON input -->
                      <textarea *ngSwitchCase="'json'" 
                        [id]="fieldName" 
                        [formControlName]="fieldName" 
                        class="form-control"
                        [class.is-invalid]="isFieldInvalid(fieldName) || getFieldValidationError(fieldName) !== null"
                        rows="3"
                        placeholder="{ }"></textarea>
                      
                      <!-- Array input -->
                      <textarea *ngSwitchCase="'array'" 
                        [id]="fieldName" 
                        [formControlName]="fieldName" 
                        class="form-control"
                        [class.is-invalid]="isFieldInvalid(fieldName) || getFieldValidationError(fieldName) !== null"
                        rows="3"
                        placeholder="[]"></textarea>
                      
                      <!-- Default text input -->
                      <input *ngSwitchDefault 
                        type="text" 
                        [id]="fieldName" 
                        [formControlName]="fieldName" 
                        class="form-control"
                        [class.is-invalid]="isFieldInvalid(fieldName) || getFieldValidationError(fieldName) !== null">
                    </ng-container>
                    
                    <!-- Validation error messages -->
                    <div *ngIf="isFieldInvalid(fieldName) || getFieldValidationError(fieldName)" class="invalid-feedback">
                      <!-- Client-side validation errors -->
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
                      
                      <!-- Server-side validation error (from API) -->
                      <div *ngIf="getFieldValidationError(fieldName)">
                        {{ getFieldValidationError(fieldName) }}
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
                <button *ngIf="entityService.canUpdate(entityType)" type="button" class="btn btn-primary me-2" (click)="goToEdit()">Edit</button>
                <button *ngIf="entityService.canDelete(entityType)" type="button" class="btn btn-danger" (click)="restService.deleteEntity(entityType, entityId)">Delete</button>
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
      
      <!-- Entity Selection Modal -->
      <div *ngIf="showModal" class="entity-modal">
        <div class="entity-modal-content">
          <div class="entity-modal-header">
            <h5>Select {{ modalEntityType }}</h5>
            <button type="button" class="btn-close" (click)="closeModal()"></button>
          </div>
          <div class="entity-modal-body">
            <div *ngIf="modalEntities.length === 0" class="text-center p-3">
              No {{ modalEntityType }} entities found.
            </div>
            <div *ngFor="let entity of modalEntities" class="entity-item" (click)="selectEntity(entity)">
              <strong>{{ entity._id }}</strong>
              <div *ngIf="entity.name">{{ entity.name }}</div>
              <div *ngIf="entity.title">{{ entity.title }}</div>
            </div>
          </div>
          <div class="entity-modal-footer">
            <button type="button" class="btn btn-secondary" (click)="closeModal()">Cancel</button>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .container-fluid { 
      padding-left: 10px;
      padding-right: 10px;
    }
    
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

    /* Style for clickable link inputs */
    .link-input {
      cursor: pointer !important;
      color: #0d6efd !important; /* Bootstrap blue */
      text-decoration: underline !important;
      background-color: transparent !important;
    }
    
    .link-input:hover {
      color: #0a58ca !important; /* Darker blue on hover */
      text-decoration: underline !important;
    }
    
    .link-input:focus {
      box-shadow: 0 0 0 0.25rem rgba(13, 110, 253, 0.25) !important;
      border-color: #86b7fe !important;
    }
    
    /* Modal styles */
    .entity-modal {
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background-color: rgba(0, 0, 0, 0.5);
      z-index: 1050;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    
    .entity-modal-content {
      background-color: #fff;
      border-radius: 8px;
      width: 80%;
      max-width: 600px;
      max-height: 80vh;
      overflow-y: auto;
      box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    }
    
    .entity-modal-header {
      padding: 15px;
      border-bottom: 1px solid #eee;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    
    .entity-modal-body {
      padding: 15px;
      max-height: 60vh;
      overflow-y: auto;
    }
    
    .entity-item {
      padding: 10px;
      border-bottom: 1px solid #eee;
      cursor: pointer;
    }
    
    .entity-item:hover {
      background-color: #f8f9fa;
    }
    
    .entity-modal-footer {
      padding: 15px;
      border-top: 1px solid #eee;
      text-align: right;
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
  
  submitting: boolean = false;
  error: string = '';
  validationErrors: ValidationError[] = [];

  // Modal properties
  showModal: boolean = false;
  modalEntities: any[] = [];
  modalFieldName: string = '';
  modalEntityType: string = '';

  mode: ViewMode = VIEW
  
  constructor(
    private route: ActivatedRoute,
    private router: Router,
    public entityService: EntityService,
    private metadataService: MetadataService,
    public formGenerator: FormGeneratorService,
    public restService: RestService,
    public viewService: ViewService,
    private navigationService: NavigationService
  ) {}
  
  // Helper methods for template conditions - delegate to ViewService
  isViewMode(): boolean {
    return this.viewService.inViewMode(this.mode);
  }
  
  isEditMode(): boolean {
    return this.viewService.inEditMode(this.mode);
  }
  
  isCreateMode(): boolean {
    return this.viewService.inCreateMode(this.mode);
  }

  ngOnInit(): void {
    // Simplified initialization
    this.route.params.subscribe(params => {
      this.entityType = params['entityType'];
      this.entityId = params['id'];
      
      const url = this.router.url;
      
      if (url.includes('/create')) {
        this.mode = CREATE
      } else if (url.includes('/edit')) {
        this.mode = EDIT
      } else {
        this.mode = VIEW
      }
      
      this.loadEntity();
    });
  }

  loadEntity(): void {
    this.error = '';
    
    // Generate the form first (same for all modes)
    const result = this.formGenerator.generateEntityForm(this.entityType, this.mode);
    this.entityForm = result.form;
    this.sortedFields = result.displayFields;
    
    // For create mode, just populate with defaults and we're done
    if (this.isCreateMode()) {
      this.populateFormValues();
      return;
    }
    
    // For edit/view mode, fetch the data first, then populate
    this.restService.getEntity(this.entityType, this.entityId).subscribe({
      next: (response) => {
        this.entity = response;
        debugger;
        
        if (!this.entity) {
          this.error = 'No entity data returned from the server.';
          return;
        }

        // Populate form with entity data for edit/view mode
        this.populateFormValues(this.entity);
      },
      error: (err) => {
        console.error('Error loading entity:', err);
        this.error = 'Failed to load entity data. Please try again later.';
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
      
      const value = this.entityService.formatFieldValue(this.entityType, fieldName, this.mode, entityData?.[fieldName]);
      control.setValue(value);
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
        
        // perform basic check using required property.  The server will perform more complex validation
        // All non-required fileds, autoGen and autoUpdate (handled by the server).  Otherwise there must be a value
        const value = control.value;
        if ( !fieldMeta!.required || (value !== undefined && value !== null && value !== '') || fieldMeta!.autoUpdate || fieldMeta!.autoGenerate) {
          processedData[fieldName] = value;
        }
      }
    } catch (error) {
      console.error('Error processing form data:', error);
    }
    
    return processedData;
  }

  /**
   * Handles API errors, including validation errors
   */
  handleApiError(err: any): void {
    this.error = '';
    this.validationErrors = [];
    
    if (err.status === 422 && err.error?.detail) {
      // Process validation errors from FastAPI (422 Unprocessable Entity)
      const errorDetail = err.error.detail;
      
      if (Array.isArray(errorDetail)) {
        // Store the validation errors directly using our ValidationError interface
        this.validationErrors = errorDetail as ValidationError[];
        
        // Mark relevant form fields as invalid
        this.validationErrors.forEach(error => {
          if (error.loc && error.loc.length > 1) {
            // Last element in loc array is the field name
            const fieldName = error.loc[error.loc.length - 1];
            
            // Check if this field exists in our form
            if (this.entityForm?.get(fieldName)) {
              // Mark the field as touched so validation message shows
              this.entityForm.get(fieldName)?.markAsTouched();
            }
          }
        });
      } else if (typeof errorDetail === 'string') {
        // Handle string error message
        this.error = errorDetail;
      }
    } else {
      // Handle other types of errors (network, server, etc.)
      this.error = err.message || 'An error occurred. Please try again.';
    }
  }
  
  /**
   * Check if a field has validation errors from the API
   */
  getFieldValidationError(fieldName: string): string | null {
    const error = this.validationErrors.find(err => 
      err.loc && err.loc.length > 1 && err.loc[err.loc.length - 1] === fieldName
    );
    return error ? error.msg : null;
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
        this.handleApiError(err);
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
        this.handleApiError(err);
        this.submitting = false;
      }
    });
  }

  goBack(): void {
    this.navigationService.goBack();
    // Explicitly return void to prevent potential issue with Angular event handlers
    return;
  }
  
  goToEdit(): void {
    if (this.entityId) {
      this.router.navigate(['/entity', this.entityType, this.entityId, 'edit']);
    }
  }
  
  /**
   * Handles click on an ObjectId field
   * In view mode: Navigate to the referenced entity
   * In edit mode: Show selector with available IDs
   */
  openLink(fieldName: string): void {
    try {
      // Check if field name follows the pattern <entity>Id
      if (!fieldName.endsWith('Id')) {
        console.error('Field name does not follow the expected pattern of <entity>Id:', fieldName);
        return;
      }
      
      const entityType = fieldName.substring(0, fieldName.length - 2);
      
      // In edit mode, show ID selector
      if (this.isEditMode()) {
        this.showIdSelector(fieldName, entityType);
        return;
      }
      
      // In view mode, navigate to the entity
      const value = this.entityForm?.get(fieldName)?.value;
      if (!value) {
        console.error('No value for field:', fieldName);
        return;
      }
      
      console.log(`Navigating to entity: ${entityType}/${value}`);
      this.entityService.viewEntity(entityType, value);
    } catch (error) {
      console.error('Error in openLink:', error);
    }
  }
  
  /**
   * Shows a selection modal with available entity IDs
   * @param fieldName Original field name (e.g., "accountId")
   * @param entityType Entity type derived from field name (e.g., "account")
   */
  showIdSelector(fieldName: string, entityType: string): void {
    // Show loading indicator
    this.error = '';
    this.submitting = true;
    
    // Fetch entities of this type
    this.restService.getEntityList(entityType).subscribe({
      next: (entities) => {
        this.submitting = false;
        // Pass the original fieldName so we can update the right form field
        this.showSelectionModal(fieldName, entityType, entities);
      },
      error: (err) => {
        console.error(`Error loading ${entityType} entities:`, err);
        this.submitting = false;
        this.error = `Failed to load ${entityType} options.`;
      }
    });
  }
  
  /**
   * Shows the entity selection modal
   */
  showSelectionModal(fieldName: string, entityType: string, entities: any[]): void {
    this.modalFieldName = fieldName;
    this.modalEntityType = entityType;
    this.modalEntities = entities;
    this.showModal = true;
  }
  
  /**
   * Selects an entity from the modal
   */
  selectEntity(entity: any): void {
    if (!this.entityForm) return;
    
    console.log('Selected entity:', entity);
    console.log('modalFieldName:', this.modalFieldName);
    
    // In our model, the field name will be something like "accountId"
    // But when we open the modal, we're currently setting modalFieldName to "_id"
    // We need to fix this by using the original field name from the form
    
    // Set the selected ID in the form field
    // Note: we need to use the original field name (e.g., "accountId"), not "_id"
    const fieldName = this.modalFieldName;
    const control = this.entityForm.get(fieldName);
    
    if (control) {
      console.log('Setting form field:', fieldName, 'to value:', entity._id);
      control.setValue(entity._id);
      control.markAsDirty();
    } else {
      console.error('Form control not found:', fieldName);
    }
    
    // Close the modal
    this.closeModal();
  }
  
  /**
   * Closes the entity selection modal
   */
  closeModal(): void {
    this.showModal = false;
  }
  
}