import { ApplicationConfig } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideHttpClient, withFetch, withInterceptors } from '@angular/common/http';
import { routes } from './app.routes';
import { ConfigService } from './services/config.service';
import { MetadataService } from './services/metadata.service';
import { EntityService } from './services/entity.service';
import { FormGeneratorService } from './services/form-generator.service';
import { RefreshService } from './services/refresh.service';
import { authInterceptor } from './interceptors/auth.interceptor';

export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(routes),
    provideHttpClient(
      withFetch(),
      withInterceptors([authInterceptor])
    ),
    // Explicitly list all services to ensure they're singletons
    ConfigService,
    MetadataService,
    EntityService,
    FormGeneratorService,
    RefreshService
  ]
};