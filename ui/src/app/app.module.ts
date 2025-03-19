import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { HttpClientModule } from '@angular/common/http';
import { RouterModule } from '@angular/router';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';

import { AppComponent } from './app.component';
import { routes } from './app.routes';

// Entity Components
import { EntitiesDashboardComponent } from './components/entity/entities-dashboard.component';
import { EntityListComponent } from './components/entity/entity-list.component';
import { EntityDetailComponent } from './components/entity/entity-detail.component';
import { EntityFormComponent } from './components/entity/entity-form.component';

// Services
import { EntityService } from './services/entity.service';
import { FormGeneratorService } from './services/form-generator.service';

@NgModule({
  declarations: [
    AppComponent,
    EntitiesDashboardComponent,
    EntityListComponent,
    EntityDetailComponent,
    EntityFormComponent
  ],
  imports: [
    BrowserModule,
    HttpClientModule,
    FormsModule,
    ReactiveFormsModule,
    CommonModule,
    RouterModule.forRoot(routes)
  ],
  providers: [
    EntityService,
    FormGeneratorService
  ],
  bootstrap: [AppComponent]
})
export class AppModule { }
