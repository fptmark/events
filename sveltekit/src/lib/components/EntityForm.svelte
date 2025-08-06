<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { metadata } from '../stores/metadata.js';
  import { rest } from '../stores/rest.js';
  import { notifications } from '../stores/notifications.js';
  import { operationResult } from '../stores/operationResult.js';
  import type { Entity, ValidationFailure, ViewMode } from '../types.js';
  import OperationResultBanner from './OperationResultBanner.svelte';
  import currency from 'currency.js';

  export let entityType: string;
  export let entityId: string = '';
  export let mode: ViewMode = 'details';

  let entity: Entity | null = null;
  let formData: Record<string, any> = {};
  let displayFields: string[] = [];
  let submitting = false;
  let error = '';
  let validationErrors: ValidationFailure[] = [];

  // Operation result banner state
  let operationMessage: string | null = null;
  let operationType: 'success' | 'error' | 'warning' | 'info' = 'success';

  // Entity selector state
  let showEntitySelector = false;
  let entitySelectorEntities: Entity[] = [];
  let entitySelectorType = '';
  let currentFieldName = '';

  $: isDetailsMode = mode === 'details';
  $: isEditMode = mode === 'edit';
  $: isCreateMode = mode === 'create';

  $: {
    if (entityType) {
      setupForm();
      checkForOperationResult();
    }
  }

  async function setupForm() {
    try {
      // Get display fields for this mode
      const entityMetadata = metadata.getEntityMetadata(entityType);
      displayFields = metadata.getViewFields(entityMetadata, mode);

      if (isCreateMode) {
        // Create mode - start with empty form
        entity = { id: '' };
        initializeFormData();
      } else if (entityId) {
        // Edit or details mode - load entity data
        const response = await rest.getEntity(entityType, entityId, mode);
        entity = response.data;
        
        if (entity) {
          initializeFormData();
          
          // Handle validation errors from server response
          if (response.notifications) {
            validationErrors = extractValidationErrors(response);
          }
        } else {
          error = 'No entity data returned from the server.';
        }
      }
    } catch (err: any) {
      console.error('Error setting up form:', err);
      error = 'Failed to load entity data.';
    }
  }

  function initializeFormData() {
    if (!entity) return;
    
    formData = {};
    displayFields.forEach(fieldName => {
      const fieldMeta = metadata.getFieldMetadata(entityType, fieldName);
      let value = entity![fieldName];

      // Handle different field types
      if (fieldMeta?.type === 'Boolean') {
        formData[fieldName] = Boolean(value);
      } else if (fieldMeta?.type === 'Currency' && value != null) {
        formData[fieldName] = currency(value).format();
      } else {
        formData[fieldName] = value || '';
      }
    });
  }

  function extractValidationErrors(response: any): ValidationFailure[] {
    // Convert API response to validation failures
    // This would need to match your Angular validation service logic
    return [];
  }

  function checkForOperationResult() {
    const result = operationResult.getOperationResultForEntity(entityType);
    if (result) {
      operationMessage = result.message;
      operationType = result.type;
      operationResult.clearOperationResult();
    }
  }

  function onBannerDismissed() {
    operationMessage = null;
  }

  function getFieldDisplayName(fieldName: string): string {
    if (fieldName === 'id') return 'ID';
    const fieldMeta = metadata.getFieldMetadata(entityType, fieldName);
    return fieldMeta?.ui?.displayName || fieldName;
  }

  function isFieldRequired(fieldName: string): boolean {
    if (fieldName === 'id') return true;
    const fieldMeta = metadata.getFieldMetadata(entityType, fieldName);
    if (!fieldMeta) return false;
    if (fieldMeta.type === 'Boolean') return false;
    return fieldMeta.required || false;
  }

  function isFieldReadOnly(fieldName: string): boolean {
    if (isDetailsMode) return true;
    if (fieldName === 'id') return true;
    
    const fieldMeta = metadata.getFieldMetadata(entityType, fieldName);
    if (!fieldMeta) return false;
    
    return fieldMeta.ui?.readOnly || 
           fieldMeta.autoGenerate || 
           fieldMeta.autoUpdate ||
           !fieldMeta.client_edit;
  }

  function getFieldOptions(fieldName: string): string[] {
    const fieldMeta = metadata.getFieldMetadata(entityType, fieldName);
    if (!fieldMeta || !fieldMeta.enum || !fieldMeta.enum.values) return [];
    return fieldMeta.enum.values;
  }

  function shouldShowSpinner(fieldName: string): boolean {
    const fieldMeta = metadata.getFieldMetadata(entityType, fieldName);
    const spinnerStep = fieldMeta?.ui?.spinnerStep;
    return spinnerStep !== undefined && spinnerStep !== 0;
  }

  function getSpinnerStep(fieldName: string): number {
    const fieldMeta = metadata.getFieldMetadata(entityType, fieldName);
    return fieldMeta?.ui?.spinnerStep || 1;
  }

  function getInputType(fieldName: string): string {
    const fieldMeta = metadata.getFieldMetadata(entityType, fieldName);
    if (!fieldMeta) return 'text';

    switch (fieldMeta.type) {
      case 'Number':
      case 'Currency':
        return 'number';
      case 'Date':
        return 'date';
      case 'Email':
        return 'email';
      case 'Password':
        return 'password';
      default:
        return 'text';
    }
  }

  async function onSubmit(event: Event) {
    event.preventDefault();
    
    if (isDetailsMode) {
      // Navigate to edit mode
      goto(`/entity/${entityType}/${entityId}/edit`);
      return;
    }

    submitting = true;
    error = '';
    validationErrors = [];
    notifications.clear();

    try {
      const submitData = prepareFormData();
      
      if (isEditMode) {
        await rest.updateEntity(entityType, entityId, submitData);
      } else if (isCreateMode) {
        await rest.createEntity(entityType, submitData);
      }

      // Success - set operation result and navigate
      const operation = isCreateMode ? 'created' : 'updated';
      const message = `${entityType} was successfully ${operation}.`;
      operationResult.setOperationResult(message, 'success', entityType);
      
      goto(`/entity/${entityType}`);
    } catch (err: any) {
      handleApiError(err);
    } finally {
      submitting = false;
    }
  }

  function prepareFormData(): Record<string, any> {
    const submitData: Record<string, any> = {};
    
    Object.keys(formData).forEach(fieldName => {
      const value = formData[fieldName];
      const fieldMeta = metadata.getFieldMetadata(entityType, fieldName);
      
      // Boolean fields: always include
      if (fieldMeta?.type === 'Boolean') {
        submitData[fieldName] = Boolean(value);
      }
      // Other fields: include non-empty values
      else if (value !== null && value !== undefined && value !== '') {
        // Convert currency fields to numbers
        if (fieldMeta?.type === 'Currency' && typeof value === 'string') {
          try {
            const currencyValue = currency(value);
            submitData[fieldName] = currencyValue.value;
          } catch (error) {
            console.warn(`Failed to parse currency value for ${fieldName}:`, value, error);
            submitData[fieldName] = value;
          }
        } else {
          submitData[fieldName] = value;
        }
      }
    });
    
    return submitData;
  }

  function handleApiError(err: any) {
    notifications.clear();
    console.log('API Error:', err);
    
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
    
    notifications.showError(errorMessage);
  }

  function goBack() {
    goto(`/entity/${entityType}`);
  }

  function openObjectIdField(fieldName: string) {
    if (!fieldName.endsWith('Id')) {
      return;
    }
    
    const relatedEntityType = fieldName.substring(0, fieldName.length - 2);
    
    if (isEditMode || isCreateMode) {
      showIdSelector(fieldName, relatedEntityType);
      return;
    }
    
    // In view mode, navigate to the related entity
    const objectIdValue = entity?.[fieldName];
    if (objectIdValue) {
      goto(`/entity/${relatedEntityType}/${objectIdValue}`);
    }
  }

  async function showIdSelector(fieldName: string, relatedEntityType: string) {
    try {
      const entities = await rest.getEntityList(relatedEntityType, mode);
      entitySelectorEntities = entities;
      entitySelectorType = relatedEntityType;
      currentFieldName = fieldName;
      showEntitySelector = true;
    } catch (err: any) {
      console.error('Error fetching entities for selector:', err);
      notifications.showError('Failed to load entities for selection');
    }
  }

  function onEntitySelected(selectedEntity: Entity) {
    if (!selectedEntity || !currentFieldName) return;
    
    formData[currentFieldName] = selectedEntity.id;
    showEntitySelector = false;
  }

  function onEntitySelectorClosed() {
    showEntitySelector = false;
  }

  onMount(() => {
    setupForm();
  });
</script>

<div class="container">
  <h2>
    {#if isCreateMode}
      Create {metadata.getTitle(entityType)}
    {:else if isEditMode}
      Edit {metadata.getTitle(entityType)}
    {:else}
      {metadata.getTitle(entityType)} Details
    {/if}
  </h2>

  <!-- Operation Result Banner -->
  {#if operationMessage}
    <OperationResultBanner
      message={operationMessage}
      type={operationType}
      on:dismissed={onBannerDismissed}
    />
  {/if}

  {#if error}
    <div class="alert alert-danger">
      {error}
    </div>
  {/if}

  <form on:submit={onSubmit}>
    {#each displayFields as fieldName}
      {@const fieldMeta = metadata.getFieldMetadata(entityType, fieldName)}
      {@const isReadOnly = isFieldReadOnly(fieldName)}
      {@const options = getFieldOptions(fieldName)}
      
      <div class="mb-3">
        <label for={fieldName} class="form-label">
          {getFieldDisplayName(fieldName)}
          {#if isFieldRequired(fieldName)}
            <span class="text-danger">*</span>
          {/if}
        </label>

        {#if fieldMeta?.type === 'Boolean'}
          <div class="form-check">
            <input
              type="checkbox"
              id={fieldName}
              class="form-check-input"
              bind:checked={formData[fieldName]}
              disabled={isReadOnly}
            />
          </div>
        {:else if options.length > 0}
          <select
            id={fieldName}
            class="form-select"
            bind:value={formData[fieldName]}
            disabled={isReadOnly}
          >
            <option value="">Select...</option>
            {#each options as option}
              <option value={option}>{option}</option>
            {/each}
          </select>
        {:else if fieldMeta?.type === 'ObjectId'}
          <div class="input-group">
            <input
              type="text"
              id={fieldName}
              class="form-control"
              bind:value={formData[fieldName]}
              readonly={isReadOnly}
            />
            {#if !isReadOnly}
              <button
                type="button"
                class="btn btn-outline-secondary"
                on:click={() => openObjectIdField(fieldName)}
              >
                Select
              </button>
            {:else}
              <button
                type="button"
                class="btn btn-outline-primary"
                on:click={() => openObjectIdField(fieldName)}
              >
                View
              </button>
            {/if}
          </div>
        {:else if fieldMeta?.type === 'Number' || fieldMeta?.type === 'Currency'}
          <input
            type="number"
            id={fieldName}
            class="form-control {shouldShowSpinner(fieldName) ? 'show-spinner' : ''}"
            bind:value={formData[fieldName]}
            readonly={isReadOnly}
            step={shouldShowSpinner(fieldName) ? getSpinnerStep(fieldName) : undefined}
          />
        {:else if fieldMeta?.type === 'Date'}
          <input
            type="date"
            id={fieldName}
            class="form-control"
            bind:value={formData[fieldName]}
            readonly={isReadOnly}
          />
        {:else if fieldMeta?.type === 'Email'}
          <input
            type="email"
            id={fieldName}
            class="form-control"
            bind:value={formData[fieldName]}
            readonly={isReadOnly}
          />
        {:else if fieldMeta?.type === 'Password'}
          <input
            type="password"
            id={fieldName}
            class="form-control"
            bind:value={formData[fieldName]}
            readonly={isReadOnly}
          />
        {:else}
          <input
            type="text"
            id={fieldName}
            class="form-control"
            bind:value={formData[fieldName]}
            readonly={isReadOnly}
          />
        {/if}
      </div>
    {/each}

    <div class="d-flex gap-2">
      <button type="button" class="btn btn-secondary" on:click={goBack}>
        Back
      </button>
      
      {#if !isDetailsMode}
        <button type="submit" class="btn btn-primary" disabled={submitting}>
          {#if submitting}
            Submitting...
          {:else if isCreateMode}
            Create
          {:else}
            Update
          {/if}
        </button>
      {:else}
        <button type="submit" class="btn btn-primary">
          Edit
        </button>
      {/if}
    </div>
  </form>
</div>

<!-- Entity Selector Modal -->
{#if showEntitySelector}
  <div class="modal-backdrop">
    <div class="modal-dialog">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">Select {entitySelectorType}</h5>
          <button type="button" class="btn-close" on:click={onEntitySelectorClosed}></button>
        </div>
        <div class="modal-body">
          <table class="table table-striped">
            <thead>
              <tr>
                <th>ID</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {#each entitySelectorEntities as selectorEntity}
                <tr>
                  <td>{selectorEntity.id}</td>
                  <td>
                    <button
                      type="button"
                      class="btn btn-primary btn-sm"
                      on:click={() => onEntitySelected(selectorEntity)}
                    >
                      Select
                    </button>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" on:click={onEntitySelectorClosed}>
            Close
          </button>
        </div>
      </div>
    </div>
  </div>
{/if}

<style>
  .container {
    max-width: 800px;
    margin: 0 auto;
    padding: 2rem;
  }

  .form-label {
    font-weight: 600;
    margin-bottom: 0.5rem;
  }

  .form-control,
  .form-select {
    display: block;
    width: 100%;
    padding: 0.375rem 0.75rem;
    font-size: 1rem;
    font-weight: 400;
    line-height: 1.5;
    color: #212529;
    background-color: #fff;
    border: 1px solid #ced4da;
    border-radius: 0.25rem;
    transition: border-color 0.15s ease-in-out, box-shadow 0.15s ease-in-out;
  }

  .form-control:focus,
  .form-select:focus {
    border-color: #86b7fe;
    outline: 0;
    box-shadow: 0 0 0 0.25rem rgba(13, 110, 253, 0.25);
  }

  .form-control:disabled,
  .form-select:disabled {
    background-color: #e9ecef;
    opacity: 1;
  }

  .form-check {
    min-height: 1.5rem;
    padding-left: 1.5em;
  }

  .form-check-input {
    width: 1em;
    height: 1em;
    margin-top: 0.25em;
    margin-left: -1.5em;
  }

  .input-group {
    position: relative;
    display: flex;
    flex-wrap: wrap;
    align-items: stretch;
    width: 100%;
  }

  .input-group .form-control {
    position: relative;
    flex: 1 1 auto;
    width: 1%;
    min-width: 0;
  }

  .input-group .btn {
    position: relative;
    z-index: 2;
  }

  .btn {
    display: inline-block;
    font-weight: 400;
    line-height: 1.5;
    text-align: center;
    text-decoration: none;
    vertical-align: middle;
    cursor: pointer;
    border: 1px solid transparent;
    padding: 0.375rem 0.75rem;
    font-size: 1rem;
    border-radius: 0.25rem;
    transition: color 0.15s ease-in-out, background-color 0.15s ease-in-out;
  }

  .btn-primary {
    color: #fff;
    background-color: #0d6efd;
    border-color: #0d6efd;
  }

  .btn-primary:hover {
    background-color: #0b5ed7;
    border-color: #0a58ca;
  }

  .btn-secondary {
    color: #fff;
    background-color: #6c757d;
    border-color: #6c757d;
  }

  .btn-secondary:hover {
    background-color: #5c636a;
    border-color: #565e64;
  }

  .btn-outline-secondary {
    color: #6c757d;
    border-color: #6c757d;
  }

  .btn-outline-secondary:hover {
    color: #fff;
    background-color: #6c757d;
    border-color: #6c757d;
  }

  .btn-outline-primary {
    color: #0d6efd;
    border-color: #0d6efd;
  }

  .btn-outline-primary:hover {
    color: #fff;
    background-color: #0d6efd;
    border-color: #0d6efd;
  }

  .btn:disabled {
    opacity: 0.65;
    cursor: not-allowed;
  }

  .btn-sm {
    padding: 0.25rem 0.5rem;
    font-size: 0.875rem;
    border-radius: 0.2rem;
  }

  .d-flex {
    display: flex;
  }

  .gap-2 {
    gap: 0.5rem;
  }

  .mb-3 {
    margin-bottom: 1rem;
  }

  .alert {
    padding: 0.75rem 1.25rem;
    margin-bottom: 1rem;
    border: 1px solid transparent;
    border-radius: 0.25rem;
  }

  .alert-danger {
    color: #721c24;
    background-color: #f8d7da;
    border-color: #f5c6cb;
  }

  .text-danger {
    color: #dc3545;
  }

  /* Modal styles */
  .modal-backdrop {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1050;
  }

  .modal-dialog {
    max-width: 500px;
    width: 90%;
    margin: 1.75rem auto;
  }

  .modal-content {
    background-color: #fff;
    border: 1px solid rgba(0, 0, 0, 0.2);
    border-radius: 0.3rem;
    box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
  }

  .modal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1rem;
    border-bottom: 1px solid #dee2e6;
  }

  .modal-title {
    margin: 0;
    font-size: 1.25rem;
    font-weight: 500;
  }

  .modal-body {
    padding: 1rem;
    max-height: 400px;
    overflow-y: auto;
  }

  .modal-footer {
    display: flex;
    justify-content: flex-end;
    padding: 1rem;
    border-top: 1px solid #dee2e6;
  }

  .btn-close {
    background: transparent;
    border: 0;
    font-size: 1.125rem;
    font-weight: 700;
    line-height: 1;
    color: #000;
    text-shadow: 0 1px 0 #fff;
    opacity: 0.5;
    cursor: pointer;
  }

  .btn-close:hover {
    opacity: 0.75;
  }

  .btn-close::before {
    content: "×";
  }

  .table {
    width: 100%;
    margin-bottom: 1rem;
    border-collapse: collapse;
  }

  .table th,
  .table td {
    padding: 0.75rem;
    vertical-align: top;
    border-top: 1px solid #dee2e6;
  }

  .table thead th {
    vertical-align: bottom;
    border-bottom: 2px solid #dee2e6;
    border-top: 0;
  }

  .table-striped tbody tr:nth-of-type(odd) {
    background-color: rgba(0, 0, 0, 0.05);
  }

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
</style>