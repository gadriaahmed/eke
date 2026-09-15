import { Component, OnInit, OnDestroy, signal, inject } from '@angular/core';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Subscription, interval } from 'rxjs';
import { ListingService, Listing, FetchSourceResult } from '../listing.service';
import { ListingsTableComponent } from '../listings-table/listings-table.component';

const POLL_INTERVAL_MS = 5 * 60 * 1000;

const ACTIONS = [
  { action: 'skip' as const,      label: 'Skip',     icon: 'close',           color: 'warn',    style: 'stroked' as const },
  { action: 'contacted' as const, label: 'Messaged', icon: 'mark_email_read', color: 'primary', style: 'flat' as const },
];

interface FetchLogEntry {
  time: string;
  sources: FetchSourceResult[];
}

@Component({
  selector: 'app-pending-page',
  standalone: true,
  imports: [MatProgressBarModule, MatIconModule, MatButtonModule, MatSnackBarModule, MatTooltipModule, ListingsTableComponent],
  template: `
    @if (fetching()) { <mat-progress-bar mode="indeterminate"></mat-progress-bar> }
    <div class="fetch-log">
      @for (entry of fetchLog(); track entry.time) {
        <div class="log-entry">
          <span class="log-time">{{ entry.time }}</span>
          @for (src of entry.sources; track src.name) {
            <span class="log-source" [class.log-error]="src.error">
              {{ src.error ? '✗' : '✓' }} {{ src.name }}: {{ src.error ?? (src.new + ' new, ' + src.filtered + ' filtered') }}
            </span>
          }
        </div>
      }
      @if (fetchLog().length === 0 && !fetching()) {
        <span class="log-empty">No fetches yet this session.</span>
      }
    </div>
    @if (rows().length === 0 && !fetching()) {
      <div class="empty"><mat-icon>search_off</mat-icon><p>No pending listings.</p></div>
    }
    <div class="table-scroll">
      <app-listings-table [rows]="rows()" [actionButtons]="buttons" (action)="onAction($event)"></app-listings-table>
    </div>
  `,
  styles: [`
    :host { display: flex; flex-direction: column; height: 100%; }
    .fetch-log {
      padding: 6px 12px;
      font-size: 12px;
      font-family: monospace;
      background: rgba(255,255,255,0.04);
      border-bottom: 1px solid rgba(255,255,255,0.08);
      display: flex;
      flex-direction: column;
      gap: 2px;
      max-height: 120px;
      overflow-y: auto;
    }
    .log-entry { display: flex; flex-wrap: wrap; gap: 4px 12px; align-items: baseline; }
    .log-time { color: #888; flex-shrink: 0; }
    .log-source { color: #aaa; }
    .log-source.log-error { color: #f66; }
    .log-empty { color: #555; }
  `],
})
export class PendingPageComponent implements OnInit, OnDestroy {
  private svc = inject(ListingService);
  private snack = inject(MatSnackBar);

  rows = signal<Listing[]>([]);
  fetching = signal(false);
  fetchLog = signal<FetchLogEntry[]>([]);
  buttons = ACTIONS;

  private sub?: Subscription;

  ngOnInit() {
    Notification.requestPermission();
    this.reload();
    this.triggerFetch();
    this.sub = interval(POLL_INTERVAL_MS).subscribe(() => this.triggerFetch());
  }

  ngOnDestroy() { this.sub?.unsubscribe(); }

  triggerFetch() {
    this.fetching.set(true);
    this.svc.runFetch().subscribe({
      next: r => {
        const now = new Date();
        const time = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        const sources: FetchSourceResult[] = r.sources ?? [{ name: 'all', new: r.new, filtered: r.filtered }];
        this.fetchLog.update(log => [{ time, sources }, ...log]);
        if (r.new > 0) {
          this.notify(r.new);
        }
        this.reload();
      },
      error: err => {
        this.fetching.set(false);
        this.snack.open('Fetch failed: ' + (err.message || err), 'Dismiss', { duration: 5000 });
        this.reload();
      },
    });
  }

  notify(count: number) {
    const ctx = new AudioContext();
    ctx.resume().then(() => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.frequency.value = 880;
      gain.gain.setValueAtTime(0.3, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.4);
      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + 0.4);
    });

    if (Notification.permission === 'granted') {
      new Notification('eke — new listings', { body: `${count} new listing(s) found!`, icon: 'favicon.ico' });
    } else {
      this.snack.open(`${count} new listing(s)!`, 'OK', { duration: 4000 });
    }
  }

  reload() {
    this.svc.getListings('pending').subscribe({
      next: r => { this.rows.set(r); this.fetching.set(false); },
      error: () => this.fetching.set(false),
    });
  }

  onAction(e: { adid: string; action: string }) {
    const row = this.rows().find(r => r.adid === e.adid)!;
    this.rows.update(ls => ls.filter(l => l.adid !== e.adid));
    const call = e.action === 'skip' ? this.svc.skip(e.adid) : this.svc.contacted(e.adid);
    call.subscribe({ error: () => { this.rows.update(ls => [row, ...ls]); } });
  }
}
