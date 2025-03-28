import { Component, OnInit } from '@angular/core';
import { FormGroup } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { EntityService, Entity, EntityMetadata } from '../../services/entity.service';
import { CommonModule } from '@angular/common';
import { ROUTE_CONFIG } from '../../constants';
import { FormGeneratorService } from '../../services/form-generator.service';
import { EntityAttributesService } from '../../services/entity-attributes.service';
import { EntityComponentService } from '../../services/entity-component.service';

@Component({
  selector: 'app-entity-form',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="container mt-4">
      <div class="d-flex justify-content-between align-items-center mb-4">
        <h2>{{ entityComponent.getTitle(metadata, entityType) }} {{ isEditMode ? 'Edit' : 'Create' }}</h2>
        <button class="btn btn-secondary" (click)="goBack()">Back</button>
      </div>
      
      <div *ngIf="loading" class="text-center">
        <p>Loading...</p>
      </div>
      
      <div *ngIf="error" class="alert alert-danger">
        {{ error }}
      </div>
      
      <div *ngIf="!loading && !error && entityForm">
        <form [formGroup]="entityForm" (ngSubmit)="onSubmit()">
          <div class="row">
            <div *ngFor="let field of sortedFields" class="col-md-6 mb-3">
              <div class="form-group">
                <label [for]="field">{{ entityComponent.getFieldDisplayName(field, metadata) }}</label>
                <ng-container [ngSwitch]="entityComponent.getFieldWidget(field, metadata)">
                  <input *ngSwitchCase="'text'" 
                         [type]="'text'" 
                         [id]="field" 
                         class="form-control" 
                         [formControlName]="field"
                         [class.is-invalid]="isFieldInvalid(field)">
                  <textarea *ngSwitchCase="'textarea'" 
                           [id]="field" 
                           class="form-control" 
                           [formControlName]="field"
                           [class.is-invalid]="isFieldInvalid(field)"></textarea>
                  <select *ngSwitchCase="'select'" 
                          [id]="field" 
                          class="form-control" 
                          [formControlName]="field"
                          [class.is-invalid]="isFieldInvalid(field)">
                    <option value="">Select...</option>
                    <option *ngFor="let option of entityComponent.getFieldOptions(field, metadata)" 
                            [value]="option">
                      {{ option }}
                    </option>
                  </select>
                  <select *ngSwitchCase="'multiselect'" 
                          [id]="field" 
                          class="form-control" 
                          [formControlName]="field"
                          multiple
                          [class.is-invalid]="isFieldInvalid(field)">
                    <option *ngFor="let option of entityComponent.getFieldOptions(field, metadata)" 
                            [value]="option">
                      {{ option }}
                    </option>
                  </select>
                </ng-container>
                <div *ngIf="isFieldInvalid(field)" class="invalid-feedback">
                  Please provide a valid value.
                </div>
              </div>
            </div>
          </div>
          
          <div class="mt-4">
            <button type="submit" 
                    class="btn btn-primary" 
                    [disabled]="entityForm.invalid || submitting">
              {{ submitting ? 'Saving...' : 'Save' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  `,
  styles: [`
    .container { max-width: 900px; }
  `]
})
export class EntityFormComponent implements OnInit {
  entityType: string = '';
  entityId: string = '';
  isEditMode: boolean = false;
  
  entity: Entity | null = null;
  metadata: EntityMetadata | null = null;
  entityForm: FormGroup | null = null;
  sortedFields: string[] = [];
  
  loading: boolean = true;
  submitting: boolean = false;
  error: string = '';

  constructor(
    public entityComponent: EntityComponentService,
    private entityService: EntityService,
    private formGenerator: FormGeneratorService,
    private route: ActivatedRoute,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.route.params.subscribe(params => {
      this.entityType = params['entityType'];
      this.entityId = params['id'];
      this.isEditMode = !!this.entityId;
      
      if (this.isEditMode) {
        this.loadEntityForEdit();
      } else {
        this.loadMetadataForCreate();
      }
    });
  }

  loadMetadataForCreate(): void {
    this.loading = true;
    this.error = '';
    
    this.entityService.getMetadata(this.entityType).subscribe({
      next: (metadata) => {
        this.metadata = metadata;
        this.initForm();
        this.loading = false;
      },
      error: (err) => {
        console.error('Error loading metadata:', err);
        this.error = 'Failed to load form configuration. Please try again later.';
        this.loading = false;
      }
    });
  }

  loadEntityForEdit(): void {
    this.loading = true;
    this.error = '';
    
    this.entityComponent.loadEntity(this.entityType, this.entityId).subscribe({
      next: (response) => {
        this.entity = response.entity;
        this.metadata = response.metadata;
        this.initForm();
        this.loading = false;
      },
      error: (err) => {
        console.error('Error loading entity:', err);
        this.error = 'Failed to load entity. Please try again later.';
        this.loading = false;
      }
    });
  }

  initForm(): void {
    if (!this.metadata) return;
    
    // Get fields that should be shown in the form
    this.sortedFields = Object.keys(this.metadata.fields).filter(field => {
      const fieldMeta = this.metadata?.fields[field];
      if (!fieldMeta) return false;
      return this.entityComponent.isValidOperation(this.metadata, 'c') && 
             this.entityComponent.initDisplayFields(this.metadata, 'form').includes(field);
    });
    
    // Generate the form
    this.entityForm = this.formGenerator.generateForm(this.metadata, this.entity);
  }

  isFieldInvalid(fieldName: string): boolean {
    if (!this.entityForm) return false;
    const control = this.entityForm.get(fieldName);
    return !!control && control.invalid && (control.dirty || control.touched);
  }

  onSubmit(): void {
    if (!this.entityForm || this.entityForm.invalid) return;
    
    this.submitting = true;
    const formData = this.entityForm.value;
    
    if (this.isEditMode) {
      this.updateEntity(formData);
    } else {
      this.createEntity(formData);
    }
  }

  createEntity(formData: any): void {
    this.entityService.createEntity(this.entityType, formData).subscribe({
      next: (result) => {
        this.submitting = false;
        this.router.navigate([ROUTE_CONFIG.getEntityDetailRoute(this.entityType, result._id)]);
      },
      error: (err) => {
        console.error('Error creating entity:', err);
        this.error = 'Failed to create entity. Please check your data and try again.';
        this.submitting = false;
      }
    });
  }

  updateEntity(formData: any): void {
    this.entityService.updateEntity(this.entityType, this.entityId, formData).subscribe({
      next: (result) => {
        this.submitting = false;
        this.router.navigate([ROUTE_CONFIG.getEntityDetailRoute(this.entityType, result._id)]);
      },
      error: (err) => {
        console.error('Error updating entity:', err);
        this.error = 'Failed to update entity. Please check your data and try again.';
        this.submitting = false;
      }
    });
  }

  goBack(): void {
    if (this.isEditMode && this.entityId) {
      this.router.navigate([ROUTE_CONFIG.getEntityDetailRoute(this.entityType, this.entityId)]);
    } else {
      this.router.navigate([ROUTE_CONFIG.getEntityListRoute(this.entityType)]);
    }
  }
}