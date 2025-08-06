<script lang="ts">
  import { page } from '$app/stores';
  import EntityForm from '$lib/components/EntityForm.svelte';

  $: entityType = $page.params.entityType || '';
  $: entityId = $page.params.id || '';
</script>

<svelte:head>
  <title>Edit {entityType}</title>
</svelte:head>

<EntityForm {entityType} {entityId} mode="edit" />