import { bootstrapApplication } from '@angular/platform-browser';
import { appConfig } from './app/app.config';
import { AppComponent } from './app/app.component';

// ---- DEV LOG SHIM (remove before prod) ----
declare const ngProdMode: any; // ignore if not present
const isDev =
  (typeof ngProdMode === 'undefined') &&  // Angular prod mode not enabled
  (location.hostname === 'localhost' || location.hostname === '127.0.0.1');

if (isDev) {
  (['log','info','warn','error'] as const).forEach((level) => {
    const orig = console[level];
    console[level] = (...args: any[]) => {
      // still show in browser console
      try { orig.apply(console, args); } catch {}

      // forward to terminal
      try {
        const safe = args.map((x) => {
          try { return typeof x === 'string' ? x : JSON.parse(JSON.stringify(x)); }
          catch { return String(x); }
        });
        fetch('http://127.0.0.1:3001/devlog', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          // keepalive avoids “page unloading” drops
          body: JSON.stringify({ level, args: safe }),
          keepalive: true,
        }).catch(() => {});
      } catch {}
    };
  });
}
// ---- END DEV LOG SHIM ----

bootstrapApplication(AppComponent, appConfig)
  .catch((err) => console.error(err));

// Delay bootstrap to allow debugger time to attach breakpoints
// setTimeout(() => {
//   console.log('Delaying bootstrap for debugging purposes.');
//   bootstrapApplication(AppComponent, appConfig)
//     .catch((err) => console.error(err));
// }, 1000);
