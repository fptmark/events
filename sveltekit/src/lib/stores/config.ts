import { writable } from 'svelte/store';

interface Config {
  apiUrl: string;
}

const createConfigStore = () => {
  const { subscribe, set, update } = writable<Config>({
    apiUrl: 'http://localhost:5500/api'
  });

  return {
    subscribe,
    set,
    update,
    getApiUrl: (path: string = '') => {
      let config: Config = { apiUrl: 'http://localhost:5500/api' };
      subscribe(value => config = value)();
      return config.apiUrl + (path ? `/${path}` : '');
    }
  };
};

export const config = createConfigStore();