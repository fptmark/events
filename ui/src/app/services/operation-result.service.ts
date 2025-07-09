import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { OperationResultType } from '../components/operation-result-banner.component';

export interface OperationResult {
  message: string;
  type: OperationResultType;
  entityType?: string;
}

@Injectable({
  providedIn: 'root'
})
export class OperationResultService {
  private operationResultSubject = new BehaviorSubject<OperationResult | null>(null);
  public operationResult$ = this.operationResultSubject.asObservable();

  constructor() {}

  /**
   * Set an operation result to be displayed on navigation
   * @param message The operation message
   * @param type The type of operation result
   * @param entityType Optional entity type for context
   */
  setOperationResult(message: string, type: OperationResultType = 'success', entityType?: string): void {
    this.operationResultSubject.next({
      message,
      type,
      entityType
    });
  }

  /**
   * Clear the current operation result
   */
  clearOperationResult(): void {
    this.operationResultSubject.next(null);
  }

  /**
   * Get the current operation result (synchronous)
   */
  getCurrentOperationResult(): OperationResult | null {
    return this.operationResultSubject.value;
  }

  /**
   * Check if there's a pending operation result for a specific entity type
   * @param entityType The entity type to check
   * @returns The operation result if it matches, null otherwise
   */
  getOperationResultForEntity(entityType: string): OperationResult | null {
    const current = this.getCurrentOperationResult();
    if (current && (!current.entityType || current.entityType === entityType)) {
      return current;
    }
    return null;
  }
}