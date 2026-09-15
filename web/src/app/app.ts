import { Component, inject, signal } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatTabsModule } from '@angular/material/tabs';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { ListingService } from './listing.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    MatToolbarModule,
    MatTabsModule,
    MatIconModule,
    MatButtonModule,
    MatTooltipModule,
    MatSnackBarModule,
  ],
  template: `
    <mat-toolbar color="primary" class="app-toolbar">
      <mat-icon style="margin-right: 8px">apartment</mat-icon>
      <span>eke — Dev</span>
      <span style="flex: 1"></span>
      <button
        mat-icon-button
        (click)="triggerFetch()"
        [disabled]="fetching()"
        matTooltip="Fetch now (excludes Immowelt & Wohnsinn)"
      >
        <mat-icon>refresh</mat-icon>
      </button>
    </mat-toolbar>

    <nav mat-tab-nav-bar [tabPanel]="tabPanel" color="accent" class="nav-tabs">
      <a
        mat-tab-link
        routerLink="/"
        routerLinkActive="active-link"
        [routerLinkActiveOptions]="{ exact: true }"
      >
        <mat-icon class="tab-icon">pending_actions</mat-icon> Pending
      </a>
      <a mat-tab-link routerLink="/skipped" routerLinkActive="active-link">
        <mat-icon class="tab-icon">cancel</mat-icon> Skipped
      </a>
      <a mat-tab-link routerLink="/contacted" routerLinkActive="active-link">
        <mat-icon class="tab-icon">mark_email_read</mat-icon> Messaged
      </a>
    </nav>

    <mat-tab-nav-panel #tabPanel class="tab-panel">
      <router-outlet></router-outlet>
    </mat-tab-nav-panel>
  `,
  styles: [
    `
      :host {
        display: flex;
        flex-direction: column;
        height: 100vh;
        overflow: hidden;
      }
      .app-toolbar {
        flex-shrink: 0;
      }
      .nav-tabs {
        flex-shrink: 0;
      }
      .tab-icon {
        margin-right: 6px;
        font-size: 18px;
        width: 18px;
        height: 18px;
        vertical-align: middle;
      }
      .tab-panel {
        flex: 1;
        overflow: hidden;
        display: flex;
        flex-direction: column;
      }
      .tab-panel > router-outlet + * {
        flex: 1;
        overflow: hidden;
      }
    `,
  ],
})
export class App {
  private svc = inject(ListingService);
  private snack = inject(MatSnackBar);
  fetching = signal(false);

  triggerFetch() {
    this.fetching.set(true);
    this.svc.runFetch().subscribe({
      next: (r) => {
        this.fetching.set(false);
        const msg = `Fetched: ${r.new} new, ${r.filtered} filtered`;
        this.snack.open(msg, r.new > 0 ? 'OK' : undefined, { duration: r.new > 0 ? 5000 : 3000 });
      },
      error: (err) => {
        this.fetching.set(false);
        this.snack.open('Fetch failed: ' + (err.message || err), 'Dismiss', { duration: 5000 });
      },
    });
  }
}
