import { Injectable } from '@angular/core';
import { Subject, Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class RefreshService {
  // Private subjects for each entity type
  private refreshSubjects: Map<string, Subject<void>> = new Map();

  constructor() {}

  /**
   * Get or create a subject for a specific entity type
   * @param entityType The type of entity to get/create a subject for
   * @returns Subject for the entity type
   */
  private getSubject(entityType: string): Subject<void> {
    if (!this.refreshSubjects.has(entityType)) {
      this.refreshSubjects.set(entityType, new Subject<void>());
    }
    return this.refreshSubjects.get(entityType)!;
  }

  /**
   * Trigger a refresh for a specific entity type
   * @param entityType The type of entity to refresh
   */
  triggerRefresh(entityType: string): void {
    console.log(`RefreshService: Triggering refresh for ${entityType}`);
    this.getSubject(entityType).next();
  }

  /**
   * Get an observable that emits when the specified entity type should be refreshed
   * @param entityType The type of entity to watch for refreshes
   * @returns Observable that emits when the entity type should be refreshed
   */
  getRefreshObservable(entityType: string): Observable<void> {
    return this.getSubject(entityType).asObservable();
  }

  /**
   * Clear all refresh subscriptions
   * This should be called when cleaning up/destroying components
   */
  clearAll(): void {
    this.refreshSubjects.forEach(subject => subject.complete());
    this.refreshSubjects.clear();
  }
} 