<script lang="ts">
  import { page } from '$app/stores';
  import EntityForm from '$lib/components/EntityForm.svelte';

  $: entityType = $page.params.entityType || '';
</script>

<svelte:head>
  <title>Create {entityType}</title>
</svelte:head>

<EntityForm {entityType} mode="create" />