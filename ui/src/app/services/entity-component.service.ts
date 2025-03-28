import { Injectable } from '@angular/core'
import { DomSanitizer, SafeHtml } from '@angular/platform-browser'
import { Entity, EntityMetadata, EntityFieldMetadata, EntityMetadataResponse } from './entity.service'
import { EntityAttributesService } from './entity-attributes.service'
import { EntityService } from './entity.service'
import { Observable } from 'rxjs'

@Injectable({
  providedIn: 'root'
})
export class EntityComponentService {
  constructor(
    private entityService: EntityService,
    private entityAttributes: EntityAttributesService,
    private sanitizer: DomSanitizer
  ) {}

  loadEntity(entityType: string, entityId: string): Observable<{ entity: Entity, metadata: EntityMetadata }> {
    return this.entityService.getEntity(entityType, entityId)
  }

  loadEntities(entityType: string): Observable<{ entities: Entity[], metadata: EntityMetadata }> {
    return this.entityService.getEntities(entityType)
  }

  deleteEntity(entityType: string, id: string): Observable<any> {
    return this.entityService.deleteEntity(entityType, id)
  }

  initDisplayFields(metadata: EntityMetadata | null, view: 'list' | 'details' | 'form'): string[] {
    if (!metadata) return []
    
    return Object.keys(metadata.fields).filter(field => {
      const fieldMeta = metadata.fields[field]
      if (!fieldMeta) return false
      return this.entityAttributes.showInView(fieldMeta, view)
    })
  }

  formatFieldValue(entity: Entity, fieldName: string, metadata: EntityMetadata | null): SafeHtml {
    if (!entity || entity[fieldName] === undefined || entity[fieldName] === null) {
      return this.sanitizer.bypassSecurityTrustHtml('')
    }
    
    const value = entity[fieldName]
    const fieldMeta = metadata?.fields[fieldName]
    if (!fieldMeta) return this.sanitizer.bypassSecurityTrustHtml(String(value))
    
    return this.sanitizer.bypassSecurityTrustHtml(
      this.entityAttributes.formatFieldValue(value, fieldMeta)
    )
  }

  getFieldDisplayName(fieldName: string, metadata: EntityMetadata | null): string {
    if (!metadata?.fields) return fieldName
    const fieldMeta = metadata.fields[fieldName]
    if (!fieldMeta) return fieldName
    return this.entityAttributes.getFieldDisplayName(fieldMeta)
  }

  getFieldWidget(fieldName: string, metadata: EntityMetadata | null): string {
    if (!metadata?.fields) return 'text'
    const fieldMeta = metadata.fields[fieldName]
    if (!fieldMeta) return 'text'
    return this.entityAttributes.getFieldWidget(fieldMeta)
  }

  getFieldOptions(fieldName: string, metadata: EntityMetadata | null): string[] {
    if (!metadata?.fields) return []
    const fieldMeta = metadata.fields[fieldName]
    if (!fieldMeta) return []
    return this.entityAttributes.getFieldOptions(fieldMeta)
  }

  getTitle(metadata: EntityMetadata | EntityMetadataResponse | null, entityType: string): string {
    if (!metadata) return entityType
    return this.entityAttributes.getTitle(metadata)
  }

  getButtonLabel(metadata: EntityMetadata | EntityMetadataResponse | null): string {
    if (!metadata) return ''
    return this.entityAttributes.getButtonLabel(metadata)
  }

  getDescription(metadata: EntityMetadata | EntityMetadataResponse | null): string {
    if (!metadata) return ''
    return this.entityAttributes.getDescription(metadata)
  }

  isValidOperation(metadata: EntityMetadata | null, operation: string): boolean {
    if (!metadata) return true // Default to allowing all operations if metadata is not loaded yet
    return this.entityAttributes.getOperations(metadata).includes(operation)
  }
} 