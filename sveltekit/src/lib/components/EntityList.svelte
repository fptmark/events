<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { metadata } from '../stores/metadata.js';
  import { rest } from '../stores/rest.js';
  import { operationResult } from '../stores/operationResult.js';
  import type { Entity } from '../types.js';
  import OperationResultBanner from './OperationResultBanner.svelte';

  export let entityType: string;

  let entities: Entity[] = [];
  let displayFields: string[] = [];
  let loading = true;
  let error = '';
  let totalCount = 0;

  // Operation result banner state
  let operationMessage: string | null = null;
  let operationType: 'success' | 'error' | 'warning' | 'info' = 'success';

  $: {
    if (entityType) {
      loadEntities();
      checkForOperationResult();
    }
  }

  async function loadEntities() {
    loading = true;
    error = '';

    try {
      // Get display fields for summary mode
      const entityMetadata = metadata.getEntityMetadata(entityType);
      displayFields = metadata.getViewFields(entityMetadata, 'summary');

      // Load entities
      const response = await rest.getEntityList(entityType, 'summary');
      entities = response;
      totalCount = response.length; // Simple count for now
      loading = false;
    } catch (err: any) {
      console.error('Error loading entities:', err);
      error = 'Failed to load entities';
      loading = false;
    }
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

  function navigateToCreate() {
    goto(`/entity/${entityType}/create`);
  }

  function navigateToDetails(id: string) {
    goto(`/entity/${entityType}/${id}`);
  }

  function navigateToEdit(id: string) {
    goto(`/entity/${entityType}/${id}/edit`);
  }

  async function deleteEntity(id: string) {
    try {
      await rest.deleteEntity(entityType, id);
      // Reload the list after successful delete
      await loadEntities();
    } catch (err) {
      console.error('Delete failed:', err);
    }
  }

  function getFieldDisplayName(fieldName: string): string {
    const fieldMeta = metadata.getFieldMetadata(entityType, fieldName);
    return fieldMeta?.ui?.displayName || fieldName;
  }

  function formatFieldValue(entity: Entity, fieldName: string): string {
    const value = entity[fieldName];
    if (value === null || value === undefined) return '';
    
    const fieldMeta = metadata.getFieldMetadata(entityType, fieldName);
    
    // Handle different field types
    if (fieldMeta?.type === 'Currency') {
      return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
      }).format(Number(value) || 0);
    }
    
    if (fieldMeta?.type === 'Date') {
      return new Date(value).toLocaleDateString();
    }
    
    if (fieldMeta?.type === 'Boolean') {
      return value ? 'Yes' : 'No';
    }

    // For ObjectId fields, check if we have embedded FK data
    if (fieldMeta?.type === 'ObjectId') {
      const showConfig = metadata.getShowConfig(entityType, fieldName, 'summary');
      if (showConfig && entity[showConfig.endpoint]) {
        const relatedEntity = entity[showConfig.endpoint];
        const displayFields = showConfig.displayInfo[0].fields;
        return displayFields.map(field => relatedEntity[field]).join(' - ');
      }
    }
    
    return String(value);
  }

  function canCreate(): boolean {
    return metadata.isValidOperation(entityType, 'c');
  }

  function canRead(): boolean {
    return metadata.isValidOperation(entityType, 'r');
  }

  function canUpdate(): boolean {
    return metadata.isValidOperation(entityType, 'u');
  }

  function canDelete(): boolean {
    return metadata.isValidOperation(entityType, 'd');
  }

  onMount(() => {
    loadEntities();
  });
</script>

<div class="mt-4">
  <h2>{metadata.getTitle(entityType)}</h2>
  
  <!-- Operation Result Banner -->
  {#if operationMessage}
    <OperationResultBanner
      message={operationMessage}
      type={operationType}
      on:dismissed={onBannerDismissed}
    />
  {/if}
  
  <!-- Create button -->
  {#if canCreate()}
    <div class="mb-3">
      <button class="btn btn-entity-create" on:click={navigateToCreate}>
        Create {entityType}
      </button>
    </div>
  {/if}
  
  {#if loading}
    <div class="text-center">
      <p>Loading...</p>
    </div>
  {:else if error}
    <div class="alert alert-danger">
      {error}
    </div>
  {:else}
    {#if entities.length === 0}
      <div class="alert alert-info">
        No {entityType} records found.
      </div>
    {:else}
      <!-- Table layout -->
      <div class="custom-table-container">
        <table class="table table-striped table-hover">
          <thead>
            <tr>
              {#each displayFields as field}
                <th>{getFieldDisplayName(field)}</th>
              {/each}
              <th class="actions-column">Actions</th>
            </tr>
          </thead>
          <tbody>
            {#each entities as entity}
              <tr>
                {#each displayFields as field}
                  <td>{formatFieldValue(entity, field)}</td>
                {/each}
                <td class="actions-column text-nowrap">
                  <div class="btn-group btn-group-sm">
                    {#if canRead()}
                      <button
                        class="btn btn-entity-details me-1"
                        on:click={() => navigateToDetails(entity.id)}
                      >
                        Details
                      </button>
                    {/if}
                    {#if canUpdate()}
                      <button
                        class="btn btn-entity-edit me-1"
                        on:click={() => navigateToEdit(entity.id)}
                      >
                        Edit
                      </button>
                    {/if}
                    {#if canDelete()}
                      <button
                        class="btn btn-entity-delete"
                        on:click={() => deleteEntity(entity.id)}
                      >
                        Delete
                      </button>
                    {/if}
                  </div>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  {/if}
</div>

<style>
  .container-fluid { 
    padding-left: 10px;
    padding-right: 10px;
  }
  
  .table-responsive {
    width: 100%;
    overflow-x: auto;
    margin-bottom: 20px;
    padding-bottom: 5px;
  }
  
  .table {
    table-layout: auto;
  }
  
  .btn-group {
    white-space: nowrap;
    display: flex;
  }
  
  td {
    max-width: 300px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    text-align: left;
  }
  
  .actions-column {
    white-space: nowrap;
    width: 200px !important;
    min-width: 200px !important;
    padding-right: 15px !important;
  }
  
  th {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  
  .table td,
  .table th {
    padding-top: 0.25rem;
    padding-bottom: 0.25rem;
    vertical-align: middle;
  }

  /* Button styles - matching Angular UI */
  .btn {
    padding: 0.25rem 0.5rem;
    font-size: 0.875rem;
    border-radius: 0.25rem;
    text-decoration: none;
    cursor: pointer;
    border: 1px solid transparent;
  }

  .btn-entity-create {
    background-color: #198754;
    border-color: #198754;
    color: white;
  }

  .btn-entity-details {
    background-color: #0d6efd;
    border-color: #0d6efd;
    color: white;
  }

  .btn-entity-edit {
    background-color: #fd7e14;
    border-color: #fd7e14;
    color: white;
  }

  .btn-entity-delete {
    background-color: #dc3545;
    border-color: #dc3545;
    color: white;
  }

  .btn:hover {
    opacity: 0.85;
  }

  .btn-group-sm .btn {
    font-size: 0.75rem;
    padding: 0.125rem 0.25rem;
  }

  .me-1 {
    margin-right: 0.25rem;
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

  .alert-info {
    color: #0c5460;
    background-color: #d1ecf1;
    border-color: #bee5eb;
  }

  .text-center {
    text-align: center;
  }

  .text-nowrap {
    white-space: nowrap;
  }

  .mb-3 {
    margin-bottom: 1rem;
  }

  .mt-4 {
    margin-top: 1.5rem;
  }
</style>