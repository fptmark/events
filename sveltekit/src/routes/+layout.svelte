<script lang="ts">
	import favicon from '$lib/assets/favicon.svg';
	import { notifications } from '$lib/stores/notifications.js';
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</svelte:head>

<!-- Global notifications -->
{#if $notifications.length > 0}
	<div class="notification-container">
		{#each $notifications as notification}
			<div class="alert alert-{notification.type} alert-dismissible fade show" role="alert">
				{notification.message}
				<button type="button" class="btn-close" on:click={() => notifications.remove(notification.id)}></button>
			</div>
		{/each}
	</div>
{/if}

<slot />

<style>
	:global(body) {
		margin: 0;
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
			'Ubuntu', 'Cantarell', 'Open Sans', 'Helvetica Neue', sans-serif;
		background-color: #f8f9fa;
	}

	.notification-container {
		position: fixed;
		top: 20px;
		right: 20px;
		z-index: 1060;
		max-width: 400px;
	}

	.alert {
		margin-bottom: 0.5rem;
	}
</style>
