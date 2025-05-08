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
}