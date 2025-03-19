export const API_CONFIG = {
  // Base API URL with no trailing slash
  baseUrl: '',
  
  // Endpoint mapping (entity type to endpoint)
  endpoints: {
    account: 'account',
    user: 'user',
    profile: 'profile',
    tagaffinity: 'tagaffinity',
    event: 'event',
    userevent: 'userevent',
    url: 'url',
    crawl: 'crawl'
  } as { [key: string]: string },
  
  // Helper function to get full API URL for an entity type
  getApiUrl(entityType: string): string {
    const endpoint = this.endpoints[entityType] || entityType;
    return `${this.baseUrl}/${endpoint}`;
  }
};

export const ROUTE_CONFIG = {
  // Base route path for entities
  entityBase: 'entity',
  
  // Helper function to get route for entity listing
  getEntityListRoute(entityType: string): string {
    return `/${this.entityBase}/${entityType}`;
  },
  
  // Helper function to get route for entity details
  getEntityDetailRoute(entityType: string, id: string): string {
    return `/${this.entityBase}/${entityType}/${id}`;
  },
  
  // Helper function to get route for entity creation
  getEntityCreateRoute(entityType: string): string {
    return `/${this.entityBase}/${entityType}/create`;
  },
  
  // Helper function to get route for entity editing
  getEntityEditRoute(entityType: string, id: string): string {
    return `/${this.entityBase}/${entityType}/${id}/edit`;
  }
};