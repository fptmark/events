import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';

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
  @Output() close = new EventEmitter<void>();
  @Output() entitySelected = new EventEmitter<any>();

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
}