// Entity types
export interface Entity {
  id: string;
  [key: string]: any;
}

// API Response types
export interface BackendApiResponse<T = any> {
  data: T;
  message: string | null;
  level: string | null;
  notifications?: any[];
  summary?: {
    error: number;
    warning: number;
    info: number;
    success: number;
  };
}

// Metadata types
export interface Metadata {
  projectName: string;
  database?: string;
  entities: Record<string, EntityMetadata>;
}

export interface EntityMetadata {
  entityLowerCase?: string;
  ui?: {
    title?: string;
    buttonLabel?: string;
    description?: string;
  };
  operations?: string;
  fields: {
    [key: string]: FieldMetadata;
  };
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
  ui?: UiFieldMetadata;
}

export interface UiFieldMetadata {
  displayName?: string;
  displayAfterField?: string;
  spinnerStep?: number;
  displayPages?: string;
  clientEdit?: boolean;
  readOnly?: boolean;
  format?: string;
  display?: string;
  show?: ShowConfig;
  [key: string]: any;
}

export interface ShowConfig {
  endpoint: string;
  displayInfo: DisplayInfo[];
}

export interface DisplayInfo {
  displayPages: string;
  fields: string[];
}

// Validation types
export interface ValidationFailure {
  field: string;
  constraint: string;
  value: any;
}

// View modes
export type ViewMode = 'details' | 'edit' | 'create' | 'summary';

// Notification types
export type NotificationType = 'error' | 'warning' | 'info' | 'success';

export interface Notification {
  id: string;
  type: NotificationType;
  message: string;
  timestamp: number;
}

// Operation result types
export type OperationResultType = 'success' | 'error' | 'warning' | 'info';

export interface OperationResult {
  message: string;
  type: OperationResultType;
  entityType: string;
}