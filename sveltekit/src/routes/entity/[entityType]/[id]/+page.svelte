<script lang="ts">
  import { page } from '$app/stores';
  import EntityForm from '$lib/components/EntityForm.svelte';

  $: entityType = $page.params.entityType || '';
  $: entityId = $page.params.id || '';
</script>

<svelte:head>
  <title>{entityType} Details</title>
</svelte:head>

<EntityForm {entityType} {entityId} mode="details" />