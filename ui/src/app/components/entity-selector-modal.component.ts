import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MetadataService } from '../services/metadata.service';
import { EntityService } from '../services/entity.service';

/**
 * Interface for column configuration
 */
export interface ColumnConfig {
  field: string;
  displayName?: string;
  bold?: boolean;
}

@Component({
  selector: 'app-entity-selector-modal',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './entity-selector-modal.component.html',
  styleUrls: ['./entity-selector-modal.component.css']
})
export class EntitySelectorModalComponent {
  @Input() visible: boolean = false;
  @Input() entityType: string = '';
  @Input() entities: any[] = [];
  @Input() displayColumns: ColumnConfig[] = [];
  @Input() fieldName: string = ''; // Add field name to fetch selector config
  @Output() close = new EventEmitter<void>();
  @Output() entitySelected = new EventEmitter<any>();
  
  constructor(
    private metadataService: MetadataService,
    private entityService: EntityService
  ) {}

  /**
   * Close the modal without selecting an entity
   */
  closeModal(): void {
    this.close.emit();
  }

  /**
   * Select an entity and close the modal
   */
  selectEntity(entity: any): void {
    this.entitySelected.emit(entity);
  }

  /**
   * Get value from entity for a given field path
   * Supports nested properties with dot notation (e.g., "address.city")
   * Formats dates using the entity service
   */
  getFieldValue(entity: any, fieldPath: string): any {
    if (!entity || !fieldPath) {
      return '';
    }

    const parts = fieldPath.split('.');
    let value = entity;

    for (const part of parts) {
      if (value == null) {
        return '';
      }
      value = value[part];
    }
    
    // Format date values (ISO date strings)
    if (typeof value === 'string' && 
        (value.match(/^\d{4}-\d{2}-\d{2}T/) || value.match(/^\d{4}-\d{2}-\d{2}/))) {
      return this.entityService.formatDateMDY(value);
    }

    return value;
  }

  /**
   * Check if entity has broken FK relationships
   * Returns true if any ObjectId field has broken FK (missing, no exists attr, or exists: false)
   */
  hasInvalidForeignKeys(entity: any): boolean {
    if (!entity) return false;
    
    // Check all properties for ObjectId patterns
    for (const [key, value] of Object.entries(entity)) {
      // Look for properties ending with 'Id' that have FK data
      if (key.endsWith('Id')) {
        // Derive the FK entity name from the field name (e.g., accountId -> account)
        const fkEntityName = key.substring(0, key.length - 2);
        
        // Check if the corresponding FK entity object exists
        const fkObject = entity[fkEntityName];
        
        if (fkObject && typeof fkObject === 'object') {
          // Cast to any to access exists property safely
          const fkData = fkObject as any;
          
          // Check if the FK object is missing exists property OR exists is false
          // Both scenarios indicate a broken FK relationship
          if (!fkData.hasOwnProperty('exists') || fkData.exists === false) {
            return true;
          }
        } else {
          // If no FK object exists at all, that's also a broken relationship
          // (unless it's an optional FK, but we'll treat missing FK data as broken)
          return true;
        }
      }
    }
    
    return false;
  }
}