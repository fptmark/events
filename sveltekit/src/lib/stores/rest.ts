import { writable } from 'svelte/store';
import type { Entity, BackendApiResponse } from '../types.js';
import { config } from './config.js';
import { notifications } from './notifications.js';
import { metadata } from './metadata.js';

const createRestStore = () => {
  const loading = writable<boolean>(false);
  const error = writable<string>('');

  const handleApiResponse = <T>(response: BackendApiResponse<T>): T => {
    notifications.handleApiResponse(response);
    return response.data;
  };

  const handleError = (err: any) => {
    notifications.clear();
    notifications.showError(err.message || 'An error occurred');
    throw err;
  };

  return {
    loading,
    error,

    async getEntity(entityType: string, id: string, mode: string): Promise<BackendApiResponse<Entity>> {
      loading.set(true);
      error.set('');

      try {
        const args = metadata.getShowViewParams(entityType, mode);
        const url = config.getApiUrl(`${entityType}/${id}`) + args;
        
        const response = await fetch(url);
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data: BackendApiResponse<Entity> = await response.json();
        loading.set(false);
        return data;
      } catch (err: any) {
        loading.set(false);
        error.set(err.message);
        handleError(err);
        throw err;
      }
    },

    async getEntityList(entityType: string, mode: string): Promise<Entity[]> {
      loading.set(true);
      error.set('');

      try {
        const args = metadata.getShowViewParams(entityType, mode);
        const url = config.getApiUrl(entityType + args);
        
        const response = await fetch(url);
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const apiResponse: BackendApiResponse<Entity[]> = await response.json();
        const data = handleApiResponse(apiResponse);
        loading.set(false);
        return data;
      } catch (err: any) {
        loading.set(false);
        error.set(err.message);
        handleError(err);
        throw err;
      }
    },

    async createEntity(entityType: string, entityData: any): Promise<Entity> {
      loading.set(true);
      error.set('');

      try {
        const response = await fetch(config.getApiUrl(entityType), {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(entityData)
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw { status: response.status, error: errorData };
        }

        const apiResponse: BackendApiResponse<Entity> = await response.json();
        const data = handleApiResponse(apiResponse);
        loading.set(false);

        // Trigger refresh after delay
        setTimeout(() => {
          // In SvelteKit, we'll handle refresh differently
          // For now, just log it
          console.log(`Would refresh ${entityType}`);
        }, 1000);

        return data;
      } catch (err: any) {
        loading.set(false);
        error.set(err.message);
        handleError(err);
        throw err;
      }
    },

    async updateEntity(entityType: string, id: string, entityData: any): Promise<Entity> {
      loading.set(true);
      error.set('');

      try {
        const response = await fetch(config.getApiUrl(`${entityType}/${id}`), {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(entityData)
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw { status: response.status, error: errorData };
        }

        const apiResponse: BackendApiResponse<Entity> = await response.json();
        const data = handleApiResponse(apiResponse);
        loading.set(false);

        setTimeout(() => {
          console.log(`Would refresh ${entityType}`);
        }, 1000);

        return data;
      } catch (err: any) {
        loading.set(false);
        error.set(err.message);
        handleError(err);
        throw err;
      }
    },

    async deleteEntity(entityType: string, id: string): Promise<void> {
      if (!confirm('Are you sure you want to delete this item?')) {
        return;
      }

      loading.set(true);
      error.set('');

      try {
        const response = await fetch(config.getApiUrl(`${entityType}/${id}`), {
          method: 'DELETE'
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw { status: response.status, error: errorData };
        }

        const apiResponse: BackendApiResponse<null> = await response.json();
        handleApiResponse(apiResponse);
        loading.set(false);

        setTimeout(() => {
          console.log(`Would refresh ${entityType}`);
        }, 1000);

      } catch (err: any) {
        loading.set(false);
        error.set(err.message);
        handleError(err);
        throw err;
      }
    }
  };
};

export const rest = createRestStore();