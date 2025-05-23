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
import { NotificationService } from '../services/notification.service';
import { NotificationComponent } from './notification.component';
import currency from 'currency.js';

@Component({
  selector: 'app-entity-form',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, EntitySelectorModalComponent, NotificationComponent],
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
    public metadataService: MetadataService,
    public formGenerator: FormGeneratorService,
    public restService: RestService,
    public viewService: ViewService,
    private navigationService: NavigationService,
    private notificationService: NotificationService
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
    
    // Boolean fields should never show a required indicator since they always have a value
    if (fieldMeta.type === 'Boolean') return false;
    
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
      
      // Get field metadata
      // const metadata = this.metadataService.getFieldMetadata(this.entityType, fieldName);
      
      // Format and display the value
      const value = this.entityService.formatFieldValue(this.entityType, fieldName, this.mode, entityData?.[fieldName]);
      control.setValue(value);
    }
  }

  onSubmit(): void {
    if (!this.entityForm) return;
    
    // For view mode, go to edit instead of submitting
    if (this.isViewMode()) {
      this.goToEdit();
      return;
    }
    
    // Clear previous error messages
    this.error = '';
    this.validationErrors = [];
    this.notificationService.clear();
    
    this.submitting = true;
    let formData = this.entityForm.value;
    
    // Process the form data before sending it to the API
    // This also validates currency fields
    formData = this.processFormData(formData);
    
    // After processing, check if any fields were marked invalid
    if (this.entityForm.invalid) {
      this.submitting = false;
      
      // Show validation error notification
      this.notificationService.showError('Please fix the validation errors below before submitting.', undefined, this.entityType);
      return;
    }
    
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
        const value = control.value;

        // Special handling for boolean fields - always include in payload
        if (fieldMeta?.type === 'Boolean') {
          // For checkboxes, convert to strict boolean value
          // This handles cases where the value might be something other than a strict boolean
          // Boolean fields should never be null or undefined, default to false if so
          processedData[fieldName] = value === null || value === undefined ? false : Boolean(value);
          continue;
        }
        
        // Special handling for Currency fields
        if (fieldMeta?.type === 'Currency') {
          // If value is null/undefined/empty string and not required, don't include it
          const isEmpty = value == null || (typeof value === 'string' && value.trim() === '');
          if (isEmpty && !fieldMeta.required) {
            processedData[fieldName] = null;
            continue;
          }
          
          // Parse currency value at submission time
          if (typeof value === 'string' && value.trim() !== '') {
            try {
              const parsed = currency(value, {
                precision: 2, 
                symbol: '$',
                decimal: '.',
                separator: ',',
                errorOnInvalid: true
              });
              
              processedData[fieldName] = parsed.value;
              processedData[fieldName] = parsed.value;
            } catch (e) {
              // If parsing fails, mark the field as invalid
              console.error('Currency parsing error:', e);
              control.setErrors({ 'currencyFormat': 'Invalid currency format. Use $X,XXX.XX or (X,XXX.XX) for negative values.' });
              
              // Show error notification
              this.notificationService.showError(`Invalid currency format in ${this.getFieldDisplayName(fieldName)}`, undefined, this.entityType);
              
              // Set this flag to make the error visible
              control.markAsTouched();
              control.markAsDirty();
              
              // Skip this field in processed data
              continue;
            }
          }
        }

        // For other field types - normal validation
        // If field is not required, or has a value, or is auto-handled by server, include it
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

    // Log the error for debugging in console
    console.error('API Error:', JSON.stringify(err, null, 2));

    if (err.status === 422 && err.error?.detail) {
      // Process validation errors from FastAPI (422 Unprocessable Entity)
      const errorDetail = err.error.detail;

      if (Array.isArray(errorDetail)) {
        // Store the validation errors directly using our ValidationError interface
        this.validationErrors = errorDetail as ValidationError[];

        // Show validation errors in the notification system
        this.notificationService.showError('Please correct the highlighted fields below.', this.validationErrors, this.entityType);

        // Mark relevant form fields as invalid
        this.validationErrors.forEach(error => {
          if (error.loc?.length > 1) {
            // Last element in loc array is the field name
            const fieldName = error.loc[error.loc.length - 1];

            // Mark the field as touched and dirty so validation message shows
            const control = this.entityForm?.get(fieldName);
            if (control) {
              control.markAsTouched();
              control.markAsDirty();
              
              // Set custom error on the control to ensure it shows up in UI
              const errors = control.errors ? { ...control.errors } : {};
              errors['server'] = error.msg;
              control.setErrors(errors);
            }
          }
        });
      } else if (typeof errorDetail === 'string') {
        // Handle string error message
        this.notificationService.showError(errorDetail);
      }
    } else {
      // For all other errors, show the full error details
      const errorMessage = err.status ?
        `Error ${err.status}: ${err.statusText}\n${err.error?.detail || err.message || JSON.stringify(err.error)}` :
        `Error: ${err.message || JSON.stringify(err)}`;
      
      this.notificationService.showError(errorMessage);
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
    
    // Show success notification
    const operation = this.isCreateMode() ? 'created' : 'updated';
    this.notificationService.showSuccess(`${this.entityType} was successfully ${operation}.`, true);
    
    // Navigate back to the entity list with skipLocationChange to force reload
    this.router.navigateByUrl('/', {skipLocationChange: true}).then(() => {
      this.router.navigate(['/entity', this.entityType]);
    });
  }

  /**
   * Common error handler for API operations
   */
  private handleApiFailure(err: any, operation: string): void {
    console.error(`Error ${operation} entity:`, err);

    // Directly use handleApiError to show all error details
    this.handleApiError(err);

    // Reset submitting flag so user can try again
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
      console.log(`openLink called for fieldName: ${fieldName}`);
      
      // Check if field name follows the pattern <entity>Id
      if (!fieldName.endsWith('Id')) {
        console.log(`Field ${fieldName} does not end with 'Id'`);
        return;
      }
      
      const entityType = fieldName.substring(0, fieldName.length - 2);
      console.log(`Derived entity type: ${entityType}`);
      
      // In edit or create mode, show ID selector
      if (this.isEditMode() || this.isCreateMode()) {
        console.log(`In edit/create mode, showing selector for ${entityType}`);
        this.showIdSelector(fieldName, entityType);
        return;
      }
      
      // In view mode, navigate to the entity
      const value = this.entityForm?.get(fieldName)?.value;
      if (!value) {
        console.log(`No value for ${fieldName}`);
        return;
      }
      
      console.log(`In view mode, navigating to ${entityType}/${value}`);
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
    // Get the show configuration for this field
    const showConfig = this.metadataService.getShowConfig(this.entityType, fieldName, this.mode);
    
    // Set up columns for the selector
    this.entitySelectorColumns = [{ field: '_id', bold: true, displayName: "Id" }];
    
    // Add columns from show config if available
    if (showConfig) {
      showConfig.displayInfo.fields.forEach(field => {
        this.entitySelectorColumns.push({ 
          field,
          displayName: this.entityService.getFieldDisplayName(entityType, field)
        });
      });
    }
    
    // Fetch entities for the selector
    this.restService.getEntityList(entityType).subscribe({
      next: (entities: any[]) => {
        // Show the entity selector modal
        this.currentFieldName = fieldName;
        this.entitySelectorType = entityType;
        this.entitySelectorEntities = entities;
        this.showEntitySelector = true;
      },
      error: (err: Error) => {
        console.error('Error fetching entities for selector:', err);
        this.notificationService.showError('Failed to load entities for selection');
      }
    });
  }
  
  /**
   * Handle entity selection from the modal
   */
  onEntitySelected(entity: any): void {
    if (!entity || !this.currentFieldName) return;
    
    // Get the form control
    const control = this.entityForm?.get(this.currentFieldName);
    if (!control) return;
    
    // Always set the ID value
    control.setValue(entity._id);
    
    // Close the selector
    this.showEntitySelector = false;
  }
  
  /**
   * Handle closing of the entity selector
   */
  onEntitySelectorClosed(): void {
    this.showEntitySelector = false;
  }
  
}