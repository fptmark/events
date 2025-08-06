<script lang="ts">
  import { page } from '$app/stores';
  import EntityList from '$lib/components/EntityList.svelte';

  $: entityType = $page.params.entityType || '';
</script>

<svelte:head>
  <title>{entityType} List</title>
</svelte:head>

<EntityList {entityType} />