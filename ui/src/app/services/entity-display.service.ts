import { Injectable } from '@angular/core';
import { EntityFieldMetadata } from './entity.service';

@Injectable({
  providedIn: 'root'
})
export class EntityDisplayService {

  constructor() { }

  showInView(fieldMetadata: EntityFieldMetadata, view: string): boolean {
    const displayPages = fieldMetadata.displayPages || '';
    if (displayPages === 'hidden') return false;
    return displayPages === '' || displayPages === 'all' || displayPages.includes(view)
  }

}