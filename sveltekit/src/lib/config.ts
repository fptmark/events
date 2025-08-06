// Configuration for the SvelteKit UI
export const config = {
  // Update this to match your Angular UI configuration
  apiUrl: 'http://localhost:3000/api',
  
  // Development vs production
  dev: import.meta.env.DEV
};

// Initialize config store on app start
import { config as configStore } from './stores/config.js';

// Set the API URL from environment or default
const apiUrl = import.meta.env.VITE_API_URL || config.apiUrl;
configStore.set({ apiUrl });