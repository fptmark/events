import adapter from '@sveltejs/adapter-node';
import preprocess from 'svelte-preprocess';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

export default {
   kit: {
      adapter: adapter()
   },
   preprocess: preprocess()
};


