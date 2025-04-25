import { Routes } from '@angular/router';
import { EntitiesDashboardComponent } from './components/entities-dashboard.component';
import { EntityListComponent } from './components/entity-list.component';
import { EntityFormComponent } from './components/entity-form.component';

export const routes: Routes = [
  { path: '', component: EntitiesDashboardComponent },
  { path: 'entity/:entityType', component: EntityListComponent },
  { path: 'entity/:entityType/create', component: EntityFormComponent },
  { path: 'entity/:entityType/:id', component: EntityFormComponent },
  { path: 'entity/:entityType/:id/edit', component: EntityFormComponent },
  { path: '**', redirectTo: '' }
];
