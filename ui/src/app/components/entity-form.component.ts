import { Component, OnInit } from '@angular/core';
import { FormGroup, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { EntityService } from '../services/entity.service';
import { MetadataService, EntityMetadata } from '../services/metadata.service';
import { FormGeneratorService } from '../services/form-generator.service';
import { CommonModule } from '@angular/common';
import { RestService } from '../services/rest.service';
import { ModeService, ViewMode, DETAILS, EDIT, CREATE } from '../services/mode.service';
import { NavigationService } from '../services/navigation.service';
import { EntitySelectorModalComponent, ColumnConfig } from './entity-selector-modal.component';
import { NotificationService, ValidationFailure, ErrorDetail } from '../services/notification.service';
import currency from 'currency.js';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { ValidationService } from '../services/validation.service';
import { EntityFormService } from '../services/entity-form.service';
import { OperationResultBannerComponent, OperationResultType } from './operation-result-banner.component';
import { OperationResultService } from '../services/operation-result.service';

@Component({
  selector: 'app-entity-form',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, EntitySelectorModalComponent, OperationResultBannerComponent],
  templateUrl: './entity-form.component.html',
  styleUrls: ['./entity-form.component.css']
})

export class EntityFormComponent implements OnInit {
  readonly ID_FIELD = 'id';

  entityType: string = '';
  entityId: string = '';
  
  entityForm: FormGroup | null = null;
  sortedFields: string[] = [];
  entity: any = null;
  
  submitting: boolean = false;
  error: string = '';
  validationErrors: ValidationFailure[] = [];

  // Operation result banner state
  operationMessage: string | null = null;
  operationType: OperationResultType = 'success';

  // Entity selection state
  showEntitySelector: boolean = false;
  entitySelectorEntities: any[] = [];
  entitySelectorType: string = '';
  currentFieldName: string = '';
  entitySelectorColumns: ColumnConfig[] = [];

  mode: ViewMode = DETAILS
  
  constructor(
    private route: ActivatedRoute,
    private router: Router,
    public entityService: EntityService,
    public metadataService: MetadataService,
    public formGenerator: FormGeneratorService,
    public restService: RestService,
    public modeService: ModeService,
    private navigationService: NavigationService,
    private notificationService: NotificationService,
    private validationService: ValidationService,
    private entityFormService: EntityFormService,
    private sanitizer: DomSanitizer,
    private operationResultService: OperationResultService
  ) {}
  
  // Helper methods for template conditions - delegate to ModeService
  isDetailsMode(): boolean {
    return this.modeService.inDetailsMode(this.mode);
  }
  
  isEditMode(): boolean {
    return this.modeService.inEditMode(this.mode);
  }
  
  isCreateMode(): boolean {
    return this.modeService.inCreateMode(this.mode);
  }

  ngOnInit(): void {
    // P1-P5 Unified Architecture
    this.route.params.subscribe(params => {
      this.entityType = params['entityType'].toLowerCase();
      this.entityId = params['id'];
      
      const url = this.router.url;
      
      if (url.includes('/create')) {
        this.mode = CREATE
      } else if (url.includes('/edit')) {
        this.mode = EDIT
      } else {
        this.mode = DETAILS
      }
      
      // Check for operation results when navigating to this entity
      this.checkForOperationResult();
      
      // Generate form (same for all modes)
      const result = this.formGenerator.generateEntityForm(this.entityType, this.mode);
      this.entityForm = result.form;
      this.sortedFields = result.displayFields;
      
      // Setup mode-specific behavior using P1-P5 functions
      this.setupMode();
    });
  }

  /**
   * P1-P5 Architecture: Setup mode-specific behavior
   */
  setupMode(): void {
    switch(this.mode) {
      case CREATE:
        this.setupCreateMode();
        break;
      case EDIT:
        this.setupEditMode();
        break;
      case DETAILS:
        this.setupDetailsMode();
        break;
    }
  }

  /**
   * Create Mode: P1 + P2 + P5 → Form with Submit
   */
  setupCreateMode(): void {
    // Create mode starts with empty form, no server data needed
    this.entity = {}; // Empty entity for create mode
    
    // P1: Populate enums (clear invalid values, though none exist in create mode)
    this.entityFormService.populateEnums(this.entityType, this.entityForm!, this.entity, this.sortedFields);
    
    // P2: ObjectId selector is available on-demand when user clicks Select
    // P5: Real-time validation will be handled by getFieldValidationError()
    
    console.log('Create mode setup complete - Form ready with Submit button');
  }

  /**
   * Edit Mode: P1 + P2 + P3 + P4 + P5 → Form with Submit
   */
  setupEditMode(): void {
    // Get entity from server with full response including notifications
    this.restService.getEntity(this.entityType, this.entityId, this.mode).subscribe({
      next: (fullResponse: any) => {
        this.entity = fullResponse.data;
        
        if (!this.entity) {
          this.error = 'No entity data returned from the server.';
          return;
        }

        // Let NotificationService handle the response for global notifications
        this.notificationService.handleApiResponse(fullResponse);

        // P4: Populate editable boxes from payload
        this.entityFormService.populateFormFields(this.entityType, this.entityForm!, this.entity, this.sortedFields, this.mode);
        
        // P3: Populate field errors below each field from payload (use FULL response)
        const validationFailures = this.validationService.convertApiErrorToValidationFailures(fullResponse, this.entityId);
        this.validationErrors = validationFailures;
        console.log('P3: Edit mode validation errors:', this.validationErrors);
        console.log('P3: Full server response:', fullResponse);
        this.entityFormService.populateFieldErrors(this.validationErrors);
        
        // P1: Populate enums (clear out/blank enum on error)
        this.entityFormService.populateEnums(this.entityType, this.entityForm!, this.entity, this.sortedFields);
        
        // P2: ObjectId selector is available on-demand when user clicks Select
        // P5: Real-time validation will be handled by getFieldValidationError()
        
        console.log('Edit mode setup complete - Form ready with Submit button');
      },
      error: (err: any) => {
        console.error('Error loading entity:', err);
        this.error = 'Failed to load entity data. Please try again later.';
      }
    });
  }

  /**
   * Details Mode: P3 + P4' → Form without Submit button
   */
  setupDetailsMode(): void {
    this.restService.getEntity(this.entityType, this.entityId, this.mode).subscribe({
      next: (fullResponse: any) => {
        this.entity = fullResponse.data;
        
        if (!this.entity) {
          this.error = 'No entity data returned from the server.';
          return;
        }

        // Let NotificationService handle the response for global notifications
        this.notificationService.handleApiResponse(fullResponse);

        // P4: Populate non-editable boxes from payload
        this.entityFormService.populateFormFields(this.entityType, this.entityForm!, this.entity, this.sortedFields, this.mode);
        
        // P3: Populate field errors below each field from payload (use FULL response)
        const validationFailures = this.validationService.convertApiErrorToValidationFailures(fullResponse, this.entityId);
        this.validationErrors = validationFailures;
        this.entityFormService.populateFieldErrors(this.validationErrors);
        
        console.log('Details mode setup complete - Form ready without Submit button');
      },
      error: (err: any) => {
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

  isFieldReadOnly(fieldName: string): boolean {
    return this.entityForm?.get(fieldName)?.disabled || false;
  }
  
  

  onSubmit(): void {
    if (!this.entityForm) return;
    
    // For view mode, go to edit instead of submitting
    if (this.isDetailsMode()) {
      this.goToEdit();
      return;
    }
    
    // Clear previous error messages and prepare for submission
    this.error = '';
    this.validationErrors = [];
    this.notificationService.clear();
    this.submitting = true;
    
    // Get form data and send to server - let server handle all validation
    const formData = this.getFormData();
    
    if (this.isEditMode()) {
      this.updateEntity(formData);
    } else if (this.isCreateMode()) {
      this.createEntity(formData);
    }
  }
  
  /**
   * Get simple form data for server submission - no client-side validation
   */
  getFormData(): Record<string, any> {
    const formData: Record<string, any> = {};
    
    if (!this.entityForm) return formData;
    
    // Extract form values with proper handling for different field types
    Object.keys(this.entityForm.controls).forEach(fieldName => {
      const control = this.entityForm?.get(fieldName);
      let value = control?.value;
      const fieldMeta = this.metadataService.getFieldMetadata(this.entityType, fieldName);
      
      // Boolean fields: always include (false is a valid value)
      if (fieldMeta?.type === 'Boolean') {
        formData[fieldName] = Boolean(value); // Ensure it's always true/false, never null
      }
      // Other fields: include all non-empty values
      else if (value !== null && value !== undefined && value !== '') {
        // Convert currency fields to numbers before sending to server
        if (fieldMeta?.type === 'Currency' && typeof value === 'string') {
          try {
            // Use currency.js to parse currency string to number
            const currencyValue = currency(value);
            formData[fieldName] = currencyValue.value;
          } catch (error) {
            console.warn(`Failed to parse currency value for ${fieldName}:`, value, error);
            // If parsing fails, send the original value and let server handle validation
            formData[fieldName] = value;
          }
        } else {
          formData[fieldName] = value;
        }
      }
    });
    
    return formData;
  }

  /**
   * Common handler for successful API operations
   */
  private handleApiSuccess(): void {
    this.submitting = false;
    
    // Set operation result in service to persist across navigation
    const operation = this.isCreateMode() ? 'created' : 'updated';
    const message = `${this.entityType} was successfully ${operation}.`;
    this.operationResultService.setOperationResult(message, 'success', this.entityType);
    
    // Use Angular router instead of full page reload
    this.router.navigate(['/entity', this.entityType]);
  }

  handleApiError(err: any): void {
    // Clear any existing notifications
    this.notificationService.clear();
    
    console.log('API Error:', err); // Debug logging
    
    // Extract error message with better fallback logic
    let errorMessage = 'An error occurred while processing your request.';
    
    if (err.error?.message) {
      errorMessage = err.error.message;
    } else if (err.message) {
      errorMessage = err.message;
    } else if (err.status === 422) {
      errorMessage = 'Validation errors occurred. Please check the form fields below.';
    } else if (err.status === 500) {
      errorMessage = 'Server error occurred. Please try again or contact support.';  
    } else if (err.status === 0 || err.name === 'HttpErrorResponse') {
      errorMessage = 'Network error. Please check your connection and try again.';
    }
    
    // Extract field-specific validation errors from server response
    const validationFailures = this.validationService.convertApiErrorToValidationFailures(err.error, this.entityId);

    if (validationFailures.length > 0) {
      // "Goto Edit Mode and use payload" - store validation errors for P3/P5 display
      this.validationErrors = validationFailures;
      
      // Show validation error notification
      this.notificationService.showError('Please fix the validation errors highlighted below.');
    } else {
      // For other errors, show the server message
      this.notificationService.showError(errorMessage);
    }
  }

  private handleApiFailure(err: any, operation: string): void {
    console.error(`Error ${operation} entity:`, err);
    
    // For HTTP errors, the REST service already handled notifications
    // Only handle validation state for form field highlighting
    if (err.status) {
      // This is an HTTP error - REST service already showed notification
      // Only extract validation failures for form field highlighting
      const validationFailures = this.validationService.convertApiErrorToValidationFailures(err.error, this.entityId);
      if (validationFailures.length > 0) {
        this.validationErrors = validationFailures;
      }
    } else {
      // Non-HTTP errors (like network failures) - handle normally
      this.handleApiError(err);
    }
    
    // Reset submitting flag
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
   * In view mode: Always perform preflight check before navigation (ignore cached exists state)
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
      
      // In view mode, always perform preflight check regardless of any cached state
      const objectIdValue = this.entity?.[fieldName];
      if (objectIdValue) {
        console.log(`Always performing preflight check for ${entityType} with ID: ${objectIdValue}`);
        this.preflightCheckAndNavigate(fieldName, entityType, objectIdValue);
      } else {
        console.log(`No ObjectId value found for ${fieldName}`);
      }
    } catch (error) {
      console.error('Error in openLink:', error);
    }
  }

  /**
   * Preflight check: Verify FK entity exists before navigation
   * If it doesn't exist, show error below field instead of navigating
   */
  preflightCheckAndNavigate(fieldName: string, entityType: string, objectIdValue: string): void {
    // Try to get the FK entity to verify it exists
    this.restService.getEntity(entityType, objectIdValue, this.mode).subscribe({
      next: (entity) => {
        // FK entity exists - safe to navigate
        console.log(`FK entity ${entityType}/${objectIdValue} exists, navigating`);
        this.router.navigate(['/entity', entityType, objectIdValue]);
      },
      error: (err) => {
        // FK entity doesn't exist - show error below field instead of navigating
        console.log(`FK entity ${entityType}/${objectIdValue} does not exist, showing error`);
        
        // Add validation error for this field to show "Entity does not exist"
        const validationError = {
          field: fieldName,
          constraint: 'Entity does not exist',
          value: objectIdValue
        };
        
        // Add to existing validation errors (don't replace them)
        if (!this.validationErrors) {
          this.validationErrors = [];
        }
        
        // Remove any existing error for this field and add the new one
        this.validationErrors = this.validationErrors.filter(error => error.field !== fieldName);
        this.validationErrors.push(validationError);
        
        console.log(`Added validation error for ${fieldName}: Entity does not exist`);
      }
    });
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
    this.entitySelectorColumns = [{ field: 'id', bold: true, displayName: "Id" }];
    
    // Add columns from show config if available
    if (showConfig) {
      showConfig.displayInfo[0].fields.forEach(field => {
        this.entitySelectorColumns.push({ 
          field,
          displayName: this.entityService.getFieldDisplayName(entityType, field)
        });
      });
    }
    
    // Fetch entities for the selector
    this.restService.getEntityList(entityType, this.mode).subscribe({
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
    control.setValue(entity.id);
    
    // Close the selector
    this.showEntitySelector = false;
  }
  
  /**
   * Handle closing of the entity selector
   */
  onEntitySelectorClosed(): void {
    this.showEntitySelector = false;
  }
  
  // Add method to determine if field should show spinner
  shouldShowSpinner(fieldName: string): boolean {
    const fieldMeta = this.metadataService.getFieldMetadata(this.entityType, fieldName);
    const spinnerStep = fieldMeta?.ui?.['spinnerStep'];
    return spinnerStep !== undefined && spinnerStep !== 0;
  }

  // Get the step value for number input spinners
  getSpinnerStep(fieldName: string): number {
    const fieldMeta = this.metadataService.getFieldMetadata(this.entityType, fieldName);
    return fieldMeta?.ui?.['spinnerStep'] || 1;
  }


  isFieldInvalid(fieldName: string): boolean {
    const control = this.entityForm?.get(fieldName);
    return !!(control && control.invalid && (control.dirty || control.touched));
  }
  
  /**
   * P5: UNIFIED validation function - handles ALL validation types
   * Used by Create Mode, Edit Mode (real-time validation)
   */
  getFieldValidationError(fieldName: string): string | null {
    if (!this.entityForm) return null;
    
    const control = this.entityForm.get(fieldName);
    if (!control) return null;
    
    // In create mode, don't show validation errors until user has interacted with field
    // or form has been submitted. In edit/details mode, always show validation errors.
    if (this.isCreateMode() && !control.dirty && !control.touched && !this.submitting) {
      return null;
    }
    
    const currentValue = control.value;
    
    // Use P5 function for unified real-time validation
    return this.entityFormService.performRealtimeValidation(
      this.entityType, 
      fieldName, 
      currentValue, 
      this.entity, 
      this.mode,
      this.validationErrors
    );
  }

  /**
   * Check if field has ANY validation error
   */
  hasFieldValidationError(fieldName: string): boolean {
    return this.getFieldValidationError(fieldName) !== null;
  }


  /**
   * Check for pending operation results for this entity type
   */
  private checkForOperationResult(): void {
    const result = this.operationResultService.getOperationResultForEntity(this.entityType);
    if (result) {
      this.operationMessage = result.message;
      this.operationType = result.type;
      // Clear the result from the service since we're now displaying it
      this.operationResultService.clearOperationResult();
    }
  }
  
  /**
   * Handle dismissing the operation result banner
   */
  onBannerDismissed(): void {
    this.operationMessage = null;
  }

  /**
   * Get clean display value without warnings for details mode
   */
  getDisplayValue(fieldName: string): any {
    if (!this.isDetailsMode() || !this.entityForm) {
      return this.entityForm?.get(fieldName)?.value || '';
    }

    return this.entityFormService.getDisplayValue(
      this.entityType, 
      fieldName, 
      this.entityForm, 
      this.entity
    );
  }

}