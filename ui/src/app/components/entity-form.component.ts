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
import { EntitySelectorModalComponent, ColumnConfig } from './entity-selector-modal.component';

@Component({
  selector: 'app-entity-form',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, EntitySelectorModalComponent],
  providers: [RestService],
  templateUrl: './entity-form.component.html',
  styleUrls: ['./entity-form.component.css']
})

export class EntityFormComponent implements OnInit {
  readonly ID_FIELD = '_id';

  entityType: string = '';
  entityId: string = '';
  
  // Removed unused variables
  entityForm: FormGroup | null = null;
  sortedFields: string[] = [];
  entity: any = null;
  
  submitting: boolean = false;
  error: string = '';
  validationErrors: ValidationError[] = [];

  // Entity selection state
  showEntitySelector: boolean = false;
  entitySelectorEntities: any[] = [];
  entitySelectorType: string = '';
  currentFieldName: string = '';
  entitySelectorColumns: ColumnConfig[] = [];

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
    return !!this.entityForm?.get(fieldName)?.invalid && 
           (!!this.entityForm?.get(fieldName)?.dirty || !!this.entityForm?.get(fieldName)?.touched);
  }
  
  isFieldReadOnly(fieldName: string): boolean {
    return this.entityForm?.get(fieldName)?.disabled || false;
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
        // If field is not required, or has a value, or is auto-handled by server, include it
        const value = control.value;
        if (!fieldMeta?.required || value !== undefined && value !== null && value !== '' || 
            fieldMeta?.autoUpdate || fieldMeta?.autoGenerate) {
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
          if (error.loc?.length > 1) {
            // Last element in loc array is the field name
            const fieldName = error.loc[error.loc.length - 1];
            
            // Mark the field as touched so validation message shows
            this.entityForm?.get(fieldName)?.markAsTouched();
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
      err.loc?.length > 1 && err.loc[err.loc.length - 1] === fieldName
    );
    return error?.msg || null;
  }

  /**
   * Common handler for successful API operations
   */
  private handleApiSuccess(): void {
    this.submitting = false;
    // Navigate back to the entity list
    this.router.navigate(['/entity', this.entityType]);
  }

  /**
   * Common error handler for API operations
   */
  private handleApiFailure(err: any, operation: string): void {
    console.error(`Error ${operation} entity:`, err);
    this.handleApiError(err);
    this.submitting = false;
  }

  createEntity(formData: any): void {
    this.restService.createEntity(this.entityType, formData).subscribe({
      next: () => this.handleApiSuccess(),
      error: (err) => this.handleApiFailure(err, 'creating')
    });
  }

  updateEntity(formData: any): void {
    this.restService.updateEntity(this.entityType, this.entityId, formData).subscribe({
      next: () => this.handleApiSuccess(),
      error: (err) => this.handleApiFailure(err, 'updating')
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
   * In edit/create mode: Show selector with available IDs
   * @param fieldName The field name
   */
  openLink(fieldName: string): void {
    try {
      // Check if field name follows the pattern <entity>Id
      if (!fieldName.endsWith('Id')) {
        return;
      }
      
      const entityType = fieldName.substring(0, fieldName.length - 2);
      
      // In edit or create mode, show ID selector
      if (this.isEditMode() || this.isCreateMode()) {
        this.showIdSelector(fieldName, entityType);
        return;
      }
      
      // In view mode, navigate to the entity
      const value = this.entityForm?.get(fieldName)?.value;
      if (!value) {
        return;
      }
      
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
    
    // Store the field name for later use when an entity is selected
    this.currentFieldName = fieldName;
    
    // Get selector fields from metadata service
    // The selector configuration is in the PARENT entity's metadata (this.entityType),
    // not in the target entity type (entityType)
    const selectorFields = this.metadataService.getSelectorFields(this.entityType, fieldName);
    
    // Always start with _id as the first column with bold formatting
    this.entitySelectorColumns = [{ field: '_id', bold: true, displayName: "Id" }];
    
    // Add additional fields from selector config if available
    if (selectorFields && selectorFields.length > 0) {
      selectorFields.forEach(field => {
        this.entitySelectorColumns.push({ field });
      });
    }
    
    // Fetch entities of this type
    this.restService.getEntityList(entityType).subscribe({
      next: (entities) => {
        this.submitting = false;
        // Show the entity selector modal
        this.entitySelectorType = entityType;
        this.entitySelectorEntities = entities;
        this.showEntitySelector = true;
      },
      error: (err) => {
        console.error(`Error loading ${entityType} entities:`, err);
        this.submitting = false;
        this.error = `Failed to load ${entityType} options.`;
      }
    });
  }
  
  /**
   * Handle entity selection from the modal
   */
  onEntitySelected(entity: any): void {
    if (!this.entityForm) return;
    
    // Set the selected ID in the form field
    const control = this.entityForm.get(this.currentFieldName);
    
    if (control) {
      control.setValue(entity._id);
      control.markAsDirty();
    }
    
    // Close the modal
    this.showEntitySelector = false;
  }
  
  /**
   * Handle closing of the entity selector
   */
  onEntitySelectorClosed(): void {
    this.showEntitySelector = false;
  }
  
}