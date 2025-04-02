import { bootstrapApplication } from '@angular/platform-browser';
import { appConfig } from './app/app.config';
import { AppComponent } from './app/app.component';

// bootstrapApplication(AppComponent, appConfig)
//   .catch((err) => console.error(err));

// Delay bootstrap to allow debugger time to attach breakpoints
setTimeout(() => {
  console.log('Delaying bootstrap for debugging purposes.');
  bootstrapApplication(AppComponent, appConfig)
    .catch((err) => console.error(err));
}, 1000);
