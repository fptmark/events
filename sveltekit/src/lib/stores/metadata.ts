import { writable, derived } from 'svelte/store';
import type { Metadata, EntityMetadata, FieldMetadata, ShowConfig, UiFieldMetadata } from '../types.js';
import { config } from './config.js';

const createMetadataStore = () => {
  const { subscribe, set, update } = writable<Metadata>({
    projectName: '',
    entities: {}
  });

  const recentEntities = writable<string[]>([]);
  const initialized = writable<boolean>(false);

  return {
    subscribe,
    set,
    update,
    recentEntities,
    initialized,

    async initialize() {
      try {
        const response = await fetch(config.getApiUrl('metadata'));
        const metadata: Metadata = await response.json();
        set(metadata);
        initialized.set(true);
        return metadata;
      } catch (error) {
        console.error('Failed to fetch metadata:', error);
        set({ projectName: '', entities: {} });
        initialized.set(true);
        throw error;
      }
    },

    addRecent(entityType: string) {
      recentEntities.update(recent => {
        const filtered = recent.filter(item => item !== entityType);
        return [entityType, ...filtered].slice(0, 3);
      });
    },

    getEntityMetadata(entityName: string): EntityMetadata {
      let metadata: Metadata = { projectName: '', entities: {} };
      subscribe(value => metadata = value)();
      
      const key = Object.keys(metadata.entities)
        .find(k => k.toLowerCase() === entityName.toLowerCase());
      
      if (!key) {
        throw new Error(`No metadata found for entity: ${entityName}`);
      }
      
      return metadata.entities[key];
    },

    getAvailableEntityTypes(): string[] {
      let metadata: Metadata = { projectName: '', entities: {} };
      subscribe(value => metadata = value)();
      return Object.keys(metadata.entities);
    },

    getEntityFields(entityType: string): string[] {
      const entityMetadata = this.getEntityMetadata(entityType);
      return Object.keys(entityMetadata.fields);
    },

    getFieldMetadata(entityType: string, fieldName: string): FieldMetadata | undefined {
      const entityMetadata = this.getEntityMetadata(entityType);
      if (!entityMetadata.fields[fieldName]) {
        console.warn(`No metadata found for field: ${fieldName} in entity: ${entityType}`);
        return undefined;
      }
      return entityMetadata.fields[fieldName];
    },

    getUiFieldMetadata(entityType: string, fieldName: string): UiFieldMetadata {
      return this.getFieldMetadata(entityType, fieldName)?.ui || {};
    },

    getTitle(entityName: string): string {
      const entityMetadata = this.getEntityMetadata(entityName);
      return entityMetadata.ui?.title || entityName;
    },

    getButtonLabel(entityName: string): string {
      return this.getEntityMetadata(entityName)?.ui?.buttonLabel || this.getTitle(entityName);
    },

    getDescription(entityName: string): string {
      return this.getEntityMetadata(entityName)?.ui?.description || this.getButtonLabel(entityName);
    },

    getProjectName(): string {
      let metadata: Metadata = { projectName: '', entities: {} };
      subscribe(value => metadata = value)();
      return metadata.projectName;
    },

    isValidOperation(entityName: string, operation: string): boolean {
      let operations = this.getEntityMetadata(entityName)?.operations || 'crud';
      operations = operations === 'all' ? 'crud' : operations;
      return operations.includes(operation);
    },

    getShowConfig(entityType: string, fieldName: string, view: string): ShowConfig | null {
      const fieldMetadata = this.getFieldMetadata(entityType, fieldName);
      if (!fieldMetadata?.ui?.show) return null;

      const showConfig = fieldMetadata.ui.show;
      const matchingDisplayInfo = showConfig.displayInfo.find(info => {
        if (!info.displayPages || info.displayPages === '' || info.displayPages === 'all') {
          return true;
        }
        return info.displayPages.includes(view);
      });

      if (!matchingDisplayInfo) return null;

      const endpoint = showConfig.endpoint || fieldName.substring(0, fieldName.length - 2);
      return {
        endpoint,
        displayInfo: [matchingDisplayInfo]
      };
    },

    getShowViewParams(entityType: string, mode: string): string {
      const viewSpec: { [key: string]: string[] } = {};
      const entityMetadata = this.getEntityMetadata(entityType);
      const displayFields = this.getViewFields(entityMetadata, mode);
      
      for (const fieldName of displayFields) {
        if (entityMetadata.fields[fieldName]?.type === 'ObjectId') {
          let showConfig = this.getShowConfig(entityType, fieldName, mode);
          
          if (!showConfig && mode === 'details') {
            showConfig = {
              endpoint: fieldName.substring(0, fieldName.length - 2), 
              displayInfo: [{displayPages: 'details', fields: ['id']}]
            };
          }
          
          if (showConfig) {
            viewSpec[showConfig.endpoint] = showConfig.displayInfo[0].fields;
          }
        }
      }
      
      if (Object.keys(viewSpec).length > 0) {
        return `?view=${encodeURIComponent(JSON.stringify(viewSpec))}`;
      }
      
      return '';
    },

    getViewFields(entityMetadata: EntityMetadata, mode: string): string[] {
      const allFields = Object.keys(entityMetadata.fields);
      return allFields.filter(fieldName => {
        const fieldMeta = entityMetadata.fields[fieldName];
        const displayPages = fieldMeta?.displayPages || fieldMeta?.ui?.displayPages || 'all';
        
        if (displayPages === 'all' || displayPages === '') return true;
        if (displayPages === 'none') return false;
        
        return displayPages.includes(mode);
      });
    }
  };
};

export const metadata = createMetadataStore();