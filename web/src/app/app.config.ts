import { ApplicationConfig, provideBrowserGlobalErrorListeners, provideZoneChangeDetection } from '@angular/core';
import { provideHttpClient } from '@angular/common/http';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { provideRouter } from '@angular/router';
import { PendingPageComponent } from './pages/pending-page.component';
import { SkippedPageComponent } from './pages/skipped-page.component';
import { ContactedPageComponent } from './pages/contacted-page.component';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideHttpClient(),
    provideAnimationsAsync(),
    provideRouter([
      { path: '', component: PendingPageComponent },
      { path: 'skipped', component: SkippedPageComponent },
      { path: 'contacted', component: ContactedPageComponent },
      { path: '**', redirectTo: '' },
    ]),
  ]
};
