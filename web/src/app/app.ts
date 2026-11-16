import { Component } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatTabsModule } from '@angular/material/tabs';
import { MatIconModule } from '@angular/material/icon';

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
  ],
  template: `
    <mat-toolbar color="primary" class="app-toolbar">
      <mat-icon style="margin-right: 8px">apartment</mat-icon>
      <span>eke — Dev</span>
      <span style="flex: 1"></span>
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
}
