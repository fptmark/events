import { Injectable } from '@angular/core';
import { EntityFieldMetadata } from './entity.service';

@Injectable({
  providedIn: 'root'
})
export class EntityDisplayService {

  constructor() { }

  showInView(fieldMetadata: EntityFieldMetadata, view: string): boolean {
    const display = fieldMetadata.display || '';
    if (display === 'hidden') return false;
    return display === '' || display === 'all' || display.includes(view)
  }

}