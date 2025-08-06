<script lang="ts">
  import { createEventDispatcher } from 'svelte';

  export let message: string;
  export let type: 'success' | 'error' | 'warning' | 'info' = 'success';

  const dispatch = createEventDispatcher();

  function dismiss() {
    dispatch('dismissed');
  }

  function getAlertClass(type: string): string {
    switch (type) {
      case 'success':
        return 'alert-success';
      case 'error':
        return 'alert-danger';
      case 'warning':
        return 'alert-warning';
      case 'info':
        return 'alert-info';
      default:
        return 'alert-info';
    }
  }
</script>

{#if message}
  <div class="alert {getAlertClass(type)} alert-dismissible" role="alert">
    {message}
    <button type="button" class="btn-close" on:click={dismiss} aria-label="Close"></button>
  </div>
{/if}

<style>
  .alert {
    padding: 0.75rem 1.25rem;
    margin-bottom: 1rem;
    border: 1px solid transparent;
    border-radius: 0.25rem;
    position: relative;
  }

  .alert-dismissible {
    padding-right: 3rem;
  }

  .alert-success {
    color: #0f5132;
    background-color: #d1e7dd;
    border-color: #badbcc;
  }

  .alert-danger {
    color: #721c24;
    background-color: #f8d7da;
    border-color: #f5c6cb;
  }

  .alert-warning {
    color: #664d03;
    background-color: #fff3cd;
    border-color: #ffecb5;
  }

  .alert-info {
    color: #0c5460;
    background-color: #d1ecf1;
    border-color: #bee5eb;
  }

  .btn-close {
    position: absolute;
    top: 0;
    right: 0;
    z-index: 2;
    padding: 0.75rem 1.25rem;
    background: transparent;
    border: 0;
    cursor: pointer;
    font-size: 1.125rem;
    font-weight: 700;
    line-height: 1;
    color: #000;
    text-shadow: 0 1px 0 #fff;
    opacity: 0.5;
  }

  .btn-close:hover {
    opacity: 0.75;
  }

  .btn-close::before {
    content: "×";
  }
</style>