<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { metadata } from '../stores/metadata.js';

  let entityTypes: string[] = [];
  let loading = true;
  let error = '';

  async function loadDashboard() {
    loading = true;
    error = '';

    try {
      // Wait for metadata to be initialized
      await metadata.initialize();
      
      // Get available entity types
      entityTypes = metadata.getAvailableEntityTypes();
      loading = false;
    } catch (err: any) {
      console.error('Error loading dashboard:', err);
      error = 'Failed to load dashboard. Please try again later.';
      loading = false;
    }
  }

  function navigateToEntity(entityType: string) {
    metadata.addRecent(entityType);
    goto(`/entity/${entityType}`);
  }

  onMount(() => {
    loadDashboard();
  });
</script>

<div class="container-fluid mt-4">
  <h2>{metadata.getProjectName()} Dashboard</h2>
  
  {#if loading}
    <div class="text-center">
      <p>Loading...</p>
    </div>
  {:else if error}
    <div class="alert alert-danger">
      {error}
    </div>
  {:else}
    <div class="row row-cols-1 row-cols-md-2 row-cols-lg-3 g-4">
      {#each entityTypes as entityType}
        <div class="col">
          <div class="card h-100">
            <div class="card-body">
              <h5 class="card-title">{metadata.getTitle(entityType)}</h5>
              <p class="card-text">{metadata.getDescription(entityType)}</p>
              <button class="btn btn-primary" on:click={() => navigateToEntity(entityType)}>
                {metadata.getButtonLabel(entityType)}
              </button>
            </div>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .container-fluid { 
    padding-left: 10px;
    padding-right: 10px;
  }

  .mt-4 {
    margin-top: 1.5rem;
  }

  .text-center {
    text-align: center;
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

  .row {
    display: flex;
    flex-wrap: wrap;
    margin-right: -0.75rem;
    margin-left: -0.75rem;
  }

  .row-cols-1 > * {
    flex: 0 0 auto;
    width: 100%;
  }

  .row-cols-md-2 > * {
    flex: 0 0 auto;
    width: 50%;
  }

  .row-cols-lg-3 > * {
    flex: 0 0 auto;
    width: 33.333333%;
  }

  .col {
    flex: 1 0 0%;
    padding-right: 0.75rem;
    padding-left: 0.75rem;
  }

  .g-4 {
    gap: 1.5rem;
  }

  .card {
    position: relative;
    display: flex;
    flex-direction: column;
    min-width: 0;
    word-wrap: break-word;
    background-color: #fff;
    background-clip: border-box;
    border: 1px solid rgba(0, 0, 0, 0.125);
    border-radius: 0.25rem;
    transition: transform 0.2s;
  }

  .card:hover {
    transform: translateY(-5px);
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
  }

  .h-100 {
    height: 100%;
  }

  .card-body {
    flex: 1 1 auto;
    padding: 1rem;
  }

  .card-title {
    margin-bottom: 0.5rem;
    font-size: 1.25rem;
    font-weight: 500;
  }

  .card-text {
    margin-bottom: 1rem;
    color: #6c757d;
  }

  .btn {
    display: inline-block;
    font-weight: 400;
    line-height: 1.5;
    color: #212529;
    text-align: center;
    text-decoration: none;
    vertical-align: middle;
    cursor: pointer;
    border: 1px solid transparent;
    padding: 0.375rem 0.75rem;
    font-size: 1rem;
    border-radius: 0.25rem;
    transition: color 0.15s ease-in-out, background-color 0.15s ease-in-out, border-color 0.15s ease-in-out, box-shadow 0.15s ease-in-out;
  }

  .btn-primary {
    color: #fff;
    background-color: #0d6efd;
    border-color: #0d6efd;
  }

  .btn-primary:hover {
    color: #fff;
    background-color: #0b5ed7;
    border-color: #0a58ca;
  }

  /* Responsive breakpoints */
  @media (min-width: 768px) {
    .row-cols-md-2 > * {
      width: 50%;
    }
  }

  @media (min-width: 992px) {
    .row-cols-lg-3 > * {
      width: 33.333333%;
    }
  }
</style>