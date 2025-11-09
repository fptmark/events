import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { ConfigService } from './config.service';
import { Observable, of, firstValueFrom } from 'rxjs';
import { tap, catchError } from 'rxjs/operators';
import { ModeService } from './mode.service';
interface Metadata {
  projectName: string;
  database?: string
  entities: Record<string, EntityMetadata>;
}

export interface EntityMetadata {
  entityLowerCase?: string;  // for internal use only
  ui?: {
    title?: string;
    buttonLabel?: string;
    description?: string;
  };
  operations?: string;
  fields: {
    [key: string]: FieldMetadata;
  };
  services?: {
    [key: string]: ServiceMetadata;
  };
}

export interface ServiceMetadata {
  entity: string;
  route: string;
  inputs: { [key: string]: string };
  outputs: string[];
  label?: string;
  default?: boolean;
  provider?: string;
}

interface DisplayInfo {
  displayPages: string;
  fields: string[];
}

export interface ShowConfig {
  endpoint: string;
  displayInfo: DisplayInfo[];
}

export interface FieldMetadata {
  type?: string;
  required?: boolean;
  autoGenerate?: boolean;
  autoUpdate?: boolean;
  client_edit?: boolean;
  displayPages?: string;
  ge?: number;
  le?: number;
  min_length?: number;
  max_length?: number;
  enum?: {
    values?: string[];
    message?: string;
  };
  pattern?: {
    regex?: string;
    message?: string;
  };
  ui?: UiFieldMetata;
}

export interface UiFieldMetata {
  displayName?: string;
  displayAfterField?: string;
  spinnerStep?: number;
  displayPages?: string;
  clientEdit?: boolean;
  readOnly?: boolean;
  format?: string;
  display?: string;    // 'hidden', 'secret'
  show?: ShowConfig;
  [key: string]: any;
}

@Injectable({
  providedIn: 'root'
})
export class MetadataService {
  private metadata: Metadata = { projectName: '', entities: {} };
  private recentEntities: string[] = [];
  private initialized = false;
  private initPromise: Promise<Metadata> | null = null;

  constructor(
    private http: HttpClient,
    private configService: ConfigService,
    private modeService: ModeService
  ) { }

  initialize(): Observable<Metadata> {
    if (this.initialized) {
      console.log('Metadata: Already initialized, returning existing data');
      return of(this.metadata);
    }

    const entitiesUrl = this.configService.getApiUrl('metadata');
    console.log('Metadata: Loading entities from:', entitiesUrl);

    const obs = this.http.get<Metadata>(entitiesUrl).pipe(
      tap((metadata: Metadata) => {
        console.log('Metadata: Entities loaded successfully:', Object.keys(metadata.entities).length, 'entities');
        this.metadata = metadata;
        this.initialized = true;
      }),
      catchError(error => {
        console.error('Metadata: Failed to fetch entities:', error);
        this.metadata = { projectName: '', entities: {} };
        this.initialized = true;
        return of(this.metadata);
      })
    );

    if (!this.initPromise) {
      this.initPromise = firstValueFrom(obs);
    }

    return obs;
  }

  async waitForInit(): Promise<Metadata> {
    if (this.initialized) {
      return this.metadata;
    }

    if (!this.initPromise) {
      this.initPromise = firstValueFrom(this.initialize());
    }

    return this.initPromise;
  }

  addRecent(entityType: string) {
    this.recentEntities = this.recentEntities.filter(item => item !== entityType);
    this.recentEntities.unshift(entityType);
    this.recentEntities = this.recentEntities.slice(0, 3);
  }

  getRecent(): string[] {
    return this.recentEntities;
  }

  getEntityMetadata(entityName: string): EntityMetadata {
    // Case-insensitive lookup by key
    const key = Object.keys(this.metadata.entities)
      .find(k => k.toLowerCase() === entityName.toLowerCase());
    if (!key) {
      throw new Error(`No metadata found for entity: ${entityName}`);
    }
    return this.metadata.entities[key];
  }

  getAvailableEntityTypes(): string[] {
    return Object.keys(this.metadata.entities);
  }

  getDatabaseType(): string {
    return this.metadata.database || '';
  }

  getEntityFields(entityType: string): string[] {
    const metadata = this.getEntityMetadata(entityType);
    return Object.keys(metadata.fields);
  }

  getFieldMetadata(entityType: string, fieldName: string): FieldMetadata | undefined {
    const metadata = this.getEntityMetadata(entityType);
    if (!metadata.fields[fieldName]) {
      console.warn(`No metadata found for field: ${fieldName} in entity: ${entityType}`);
      return undefined;
    }
    return metadata.fields[fieldName];
  }

  getUiFieldMetadata(entityType: string, fieldName: string): UiFieldMetata {
    return this.getFieldMetadata(entityType, fieldName)?.ui || {};
  }

  getTitle(entityName: string): string {
    const metadata = this.getEntityMetadata(entityName);
    return metadata.ui?.title || entityName;
  }

  getButtonLabel(entityName: string): string {
    return this.getEntityMetadata(entityName)?.ui?.buttonLabel || this.getTitle(entityName);
  }

  getDescription(entityName: string): string {
    return this.getEntityMetadata(entityName)?.ui?.description || this.getButtonLabel(entityName);
  }

  getProjectName(): string {
    return this.metadata.projectName;
  }

  isValidOperation(entityName: string, operation: string): boolean {
    let operations = this.getEntityMetadata(entityName)?.operations || 'crud';
    operations = operations === 'all' ? 'crud' : operations;
    return operations.includes(operation);
  }

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
  }

  getShowViewParams(entityType: string, mode: string): string {
    // Build JSON view parameter for FK fields
    const viewSpec: { [key: string]: string[] } = {};
    const entityMetadata = this.getEntityMetadata(entityType);
    const displayFields = this.modeService.getViewFields(entityMetadata, mode);
    
    for (const fieldName of displayFields) {
      // Skip the primary key 'id' field - it's not a foreign key
      if (fieldName === 'id') continue;

      // For each field that is an ObjectId (foreign key)
      if (entityMetadata.fields[fieldName]?.type === 'ObjectId') {
        let showConfig = this.getShowConfig(entityType, fieldName, mode);
        
        // Force a synthetic show config for details mode so we know if the FK exists
        if (!showConfig && this.modeService.inDetailsMode(mode)) {
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
    
    // Convert viewSpec to new format: entity1(field1,field2),entity2(field3,field4)
    if (Object.keys(viewSpec).length > 0) {
      const viewParts = Object.entries(viewSpec).map(([entity, fields]) =>
        `${entity}(${fields.join(',')})`
      );
      return `?view=${viewParts.join(',')}`;
    }

    return '';
  }

  /**
   * Search all entities for a service by name (e.g., "authn")
   * Matches service names that start with the search string
   * e.g., searching for "authn" will match "authn.cookies.redis"
   * Returns the service metadata if found, null otherwise
   */
  getService(serviceName: string): ServiceMetadata | null {
    for (const entityName of Object.keys(this.metadata.entities)) {
      const entity = this.metadata.entities[entityName];
      if (entity.services) {
        // Check for exact match first
        if (entity.services[serviceName]) {
          return entity.services[serviceName];
        }

        // Check for services that start with the search string
        for (const serviceKey of Object.keys(entity.services)) {
          if (serviceKey.startsWith(serviceName + '.') || serviceKey === serviceName) {
            return entity.services[serviceKey];
          }
        }
      }
    }
    return null;
  }

  /**
   * Get all instances of a service across entities (e.g., all "authn" configs)
   * Returns array sorted by default flag (default first)
   */
  getAllServices(serviceName: string): ServiceMetadata[] {
    const services: ServiceMetadata[] = [];

    for (const entityName of Object.keys(this.metadata.entities)) {
      const entity = this.metadata.entities[entityName];
      if (entity.services) {
        for (const serviceKey of Object.keys(entity.services)) {
          if (serviceKey === serviceName || serviceKey.startsWith(serviceName + '.')) {
            services.push(entity.services[serviceKey]);
          }
        }
      }
    }

    // Sort by default flag (default=true first)
    return services.sort((a, b) => {
      if (a.default && !b.default) return -1;
      if (!a.default && b.default) return 1;
      return 0;
    });
  }

}
