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

@Component({
  selector: 'app-entity-form',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, EntitySelectorModalComponent],
  templateUrl: './entity-form.component.html',
  styleUrls: ['./entity-form.component.css'],
  styles: [`
    /* Hide spinners by default */
    input::-webkit-outer-spin-button,
    input::-webkit-inner-spin-button {
      -webkit-appearance: none;
      margin: 0;
    }
    input[type=number] {
      -moz-appearance: textfield;
    }

    /* Show spinners only when the class is present */
    .show-spinner::-webkit-outer-spin-button,
    .show-spinner::-webkit-inner-spin-button {
      -webkit-appearance: inner-spin-button;
      margin: 0;
    }
    .show-spinner {
      -moz-appearance: spinner-textfield;
    }
  `]
})

export class EntityFormComponent implements OnInit {
  readonly ID_FIELD = '_id';

  entityType: string = '';
  entityId: string = '';
  
  entityForm: FormGroup | null = null;
  sortedFields: string[] = [];
  entity: any = null;
  
  submitting: boolean = false;
  error: string = '';
  validationErrors: ValidationFailure[] = [];

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
    private sanitizer: DomSanitizer
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
    // Simplified initialization
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
    this.restService.getEntity(this.entityType, this.entityId, this.mode).subscribe({
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

  isFieldReadOnly(fieldName: string): boolean {
    return this.entityForm?.get(fieldName)?.disabled || false;
  }
  
  
  /**
   * Populates form values based on mode and entity data
   * @param entityData Optional entity data for edit/view modes
   */
  populateFormValues(entityData?: any): void {
    if (!this.entityForm || !this.sortedFields.length) return;

    for( const fieldName of this.sortedFields) {
      const control = this.entityForm.get(fieldName);
      if (!control) continue;
      
      // Get field metadata
      const metadata = this.metadataService.getFieldMetadata(this.entityType, fieldName);
      const rawValue = entityData?.[fieldName];

      // Check if it's an ObjectId field with a show configuration for the current mode
      const showConfig = metadata?.ui?.show ? this.metadataService.getShowConfig(this.entityType, fieldName, this.mode) : null;

      // force the type to text for id fields
      let type = (fieldName === 'id') ? 'text' : metadata?.type || 'text'
      console.log(`Processing field ${fieldName} of type ${type} with raw value:`, rawValue);
      
      if (type === 'ObjectId' && showConfig) {
        // For ObjectId fields with show config, use embedded FK data
        const formattedValue = this.entityService.formatObjectIdValueWithEmbeddedData(
          this.entityType, fieldName, this.mode, rawValue, entityData, showConfig
        );
        
        // If it's in details mode, sanitize the HTML output
        if (this.isDetailsMode()) {
          control.setValue(this.sanitizer.bypassSecurityTrustHtml(formattedValue));
        } else {
          control.setValue(formattedValue);
        }
      } else {
        // For other field types or ObjectId without show config, use the synchronous formatter
        console.log(`Formatting field ${fieldName} with raw value:`, rawValue);
        const formattedValue = this.entityService.formatFieldValue(this.entityType, fieldName, this.mode, rawValue);
        
        // If it's an ObjectId field in details mode (without show config), sanitize the HTML
        if (type === 'ObjectId' && this.isDetailsMode()) {
           control.setValue(this.sanitizer.bypassSecurityTrustHtml(formattedValue));
        } else {
          control.setValue(formattedValue);
        }
      }
    }
  }

  onSubmit(): void {
    if (!this.entityForm) return;
    
    // For view mode, go to edit instead of submitting
    if (this.isDetailsMode()) {
      this.goToEdit();
      return;
    }
    
    // Clear previous error messages
    this.error = '';
    this.validationErrors = [];
    this.notificationService.clear();
    
    this.submitting = true;
    
    // Process the form data before sending it to the API
    const formData = this.processFormData();
    
    // After processing, check if any fields were marked invalid
    if (this.entityForm.invalid) {
      this.submitting = false;
      
      // Show validation error notification with form validation errors
      const invalidControls = Object.keys(this.entityForm.controls)
        .filter(key => this.entityForm?.get(key)?.errors)
        .map(field => {
          const fieldControl = this.entityForm?.get(field);
          return {
            field,
            constraint: Object.keys(fieldControl?.errors || {})
              .map(key => this.validationService.getValidationMessage(this.entityType, field, {[key]: fieldControl?.errors?.[key]}) || '')
              .join(', '),
            value: fieldControl?.value
          };
        });

      this.notificationService.showError({
        message: 'Please fix the validation errors below before submitting.',
        error_type: 'validation_error',
        context: {
          entity: this.entityType,
          invalid_fields: invalidControls
        }
      });
      return;
    }
    
    if (this.isEditMode()) {
      this.updateEntity(formData);
    } else if (this.isCreateMode()) {
      this.createEntity(formData);
    }
  }
  
  // Process form data before submitting to the API
  processFormData(): Record<string, any> {
    const processedData: Record<string, any> = {};

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
        
        const isEmpty = value === undefined || value === null || (typeof value === 'string' && value.trim() === '');
        if (isEmpty && !fieldMeta?.required) {
          continue;
        }

        // Special handling for Currency fields
        if (fieldMeta?.type === 'Currency') {
          
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
            } catch (e) {
              // If parsing fails, mark the field as invalid
              console.error('Currency parsing error:', e);
              control.setErrors({ 'currencyFormat': 'Invalid currency format. Use $X,XXX.XX or (X,XXX.XX) for negative values.' });
              
              // Show error notification
              this.notificationService.showError({
                message: `Invalid currency format in ${this.getFieldDisplayName(fieldName)}`,
                error_type: 'validation_error',
                context: {
                  entity: this.entityType,
                  invalid_fields: [{
                    field: fieldName,
                    constraint: 'Invalid currency format. Use $X,XXX.XX or (X,XXX.XX) for negative values.'
                  }]
                }
              });
              
              // Set this flag to make the error visible
              control.markAsTouched();
              control.markAsDirty();
              
              // Skip this field in processed data
              continue;
            }
          }
        }

        // For all other field types
        // Include field if it's auto-generated/updated, required, or has a value
        if (fieldMeta?.autoUpdate || fieldMeta?.autoGenerate || fieldMeta?.required || !isEmpty) {
            processedData[fieldName] = isEmpty ? null : value;
        }
      }
    } catch (error) {
      console.error('Error processing form data:', error);
    }

    return processedData;
  }

  /**
   * Common handler for successful API operations
   */
  private handleApiSuccess(): void {
    this.submitting = false;
    
    // Show success notification
    const operation = this.isCreateMode() ? 'created' : 'updated';
    this.notificationService.showSuccess(`${this.entityType} was successfully ${operation}.`, true);
    
    // Use Angular router instead of full page reload
    this.router.navigate(['/entity', this.entityType]);
  }

  handleApiError(err: any): void {
    // Clear any existing notifications
    this.notificationService.clear();
    
    // Extract error message from server response
    const errorMessage = err.error?.detail || 'An error occurred while processing your request.';
    
    // Try to extract field-specific validation errors regardless of status code
    const validationFailures = this.validationService.convertApiErrorToValidationFailures(err);
    
    if (validationFailures.length > 0) {
      // Handle structured validation errors
      this.validationErrors = validationFailures;
      
      // Mark form fields as invalid with server errors
      validationFailures.forEach((error: ValidationFailure) => {
        const control = this.entityForm?.get(error.field);
        if (control) {
          control.markAsTouched();
          control.markAsDirty();
          control.setErrors({ server: error.constraint });
        }
      });
      
      // Show validation error notification
      this.notificationService.showError('Please fix the validation errors highlighted below.');
    } else {
      // For other errors, show the server message
      this.notificationService.showError(errorMessage);
    }
  }

  private handleApiFailure(err: any, operation: string): void {
    console.error(`Error ${operation} entity:`, err);
    
    // Handle form validation state
    this.handleApiError(err);
    
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
  
  getFieldValidationError(fieldName: string): string | null {
    const control = this.entityForm?.get(fieldName);
    return control?.errors?.['server'] || null;
  }

}