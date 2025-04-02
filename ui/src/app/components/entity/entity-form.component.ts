import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { Entity, EntityMetadata, EntityFieldMetadata } from '../../services/entity.service';
import { EntityService } from '../../services/entity.service';
import { EntityComponentService } from '../../services/entity-component.service';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-entity-form',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
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
                <label [for]="field">{{ entityComponent.getFieldDisplayName(field) }}</label>
                <ng-container [ngSwitch]="entityComponent.getFieldWidget(field)">
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
                    <option *ngFor="let option of entityComponent.getFieldOptions(field)" 
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
                    <option *ngFor="let option of entityComponent.getFieldOptions(field)" 
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
  entityId: string | null = null;
  entity: Entity | null = null;
  metadata!: EntityMetadata;
  fields: { [key: string]: EntityFieldMetadata } | null = null;
  entityForm: FormGroup;
  displayFields: string[] = [];
  validationMessages: { [key: string]: string } = {};
  isEditMode: boolean = false;
  
  loading: boolean = true;
  submitting: boolean = false;
  error: string = '';
  sortedFields: string[] = [];

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private fb: FormBuilder,
    private entityService: EntityService,
    public entityComponent: EntityComponentService
  ) {
    this.entityForm = this.fb.group({});
  }

  ngOnInit(): void {
    this.route.params.subscribe(params => {
      this.entityType = params['entityType'];
      this.entityId = params['id'] || null;
      this.isEditMode = !!this.entityId;
      this.loadEntity();
    });
  }

  private loadEntity(): void {
    if (this.entityId) {
      this.loading = true;
      this.error = '';
      
      this.entityComponent.loadEntity(this.entityType, this.entityId).subscribe({
        next: ({ entity, metadata }) => {
          this.entity = entity;
          this.metadata = metadata;
          this.initForm();
          this.loading = false;
        },
        error: (err) => {
          console.error('Error loading entity:', err);
          this.error = 'Failed to load entity. Please try again later.';
          this.loading = false;
        }
      });
    } else {
      this.loading = true;
      this.error = '';
      
      this.entityComponent.loadEntities(this.entityType).subscribe({
        next: ({ metadata }) => {
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
  }

  private initForm(): void {
    if (!this.metadata) return;

    const formControls: { [key: string]: any } = {};
    this.displayFields = Object.keys(this.entity || {});

    this.displayFields.forEach(field => {
      formControls[field] = [this.entity?.[field] || '', []];
    });

    this.entityForm = this.fb.group(formControls);
  }

  isFieldInvalid(fieldName: string): boolean {
    if (!this.entityForm) return false;
    const control = this.entityForm.get(fieldName);
    return !!control && control.invalid && (control.dirty || control.touched);
  }

  onSubmit(): void {
    if (this.entityForm.valid) {
      const entity = this.entityForm.value;
      if (this.entityId) {
        this.updateEntity(entity);
      } else {
        this.createEntity(entity);
      }
    }
  }

  createEntity(formData: any): void {
    this.submitting = true;
    this.error = '';
    
    this.entityService.createEntity(this.entityType, formData).subscribe({
      next: (result) => {
        this.submitting = false;
        this.router.navigate(['/entities', this.entityType]);
      },
      error: (err) => {
        console.error('Error creating entity:', err);
        this.error = 'Failed to create entity. Please check your data and try again.';
        this.submitting = false;
      }
    });
  }

  updateEntity(formData: any): void {
    this.submitting = true;
    this.error = '';
    
    if (!this.entityId) return;
    
    this.entityService.updateEntity(this.entityType, this.entityId, formData).subscribe({
      next: (result) => {
        this.submitting = false;
        this.router.navigate(['/entities', this.entityType]);
      },
      error: (err) => {
        console.error('Error updating entity:', err);
        this.error = 'Failed to update entity. Please try again later.';
        this.submitting = false;
      }
    });
  }

  goBack(): void {
    if (this.isEditMode && this.entityId) {
      this.router.navigate(['/entities', this.entityType, this.entityId]);
    } else {
      this.router.navigate(['/entities', this.entityType]);
    }
  }

  getFieldDisplayName(fieldName: string): string {
    return fieldName;
  }

  getValidationMessage(fieldName: string): string {
    return this.validationMessages[fieldName] || '';
  }
}