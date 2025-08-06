import { writable, get } from 'svelte/store';
import type { OperationResult } from '../types.js';

const createOperationResultStore = () => {
  const store = writable<OperationResult | null>(null);

  return {
    subscribe: store.subscribe,
    
    setOperationResult(message: string, type: 'success' | 'error' | 'warning' | 'info', entityType: string) {
      store.set({ message, type, entityType });
    },

    getOperationResultForEntity(entityType: string): OperationResult | null {
      const current = get(store);
      return current && current.entityType === entityType ? current : null;
    },

    clearOperationResult() {
      store.set(null);
    }
  };
};

export const operationResult = createOperationResultStore();