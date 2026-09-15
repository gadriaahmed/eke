import { Component, Input, Output, EventEmitter } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Listing } from '../listing.service';

@Component({
  selector: 'app-listing-card',
  standalone: true,
  imports: [
    MatCardModule,
    MatButtonModule,
    MatChipsModule,
    MatIconModule,
    MatTooltipModule,
  ],
  template: `
    <mat-card appearance="outlined" class="listing-card">
      <mat-card-header>
        <mat-card-title>
          <a [href]="listing.url" target="_blank" rel="noopener" class="title-link">
            {{ listing.title || '(no title)' }}
          </a>
        </mat-card-title>
        <mat-card-subtitle class="source-subtitle">
          @if (sourceIcon(listing.search_name)) {
            <img
              [src]="sourceIcon(listing.search_name)"
              [alt]="listing.search_name?.trim()"
              [matTooltip]="listing.search_name?.trim()"
              class="source-icon"
              (error)="onIconError($event)"
            />
          } @else {
            <span>{{ listing.search_name?.trim() }}</span>
          }
        </mat-card-subtitle>
      </mat-card-header>

      <mat-card-content>
        <mat-chip-set>
          @if (listing.price) {
            <mat-chip><mat-icon matChipAvatar>euro</mat-icon>{{ listing.price }}</mat-chip>
          }
          @if (listing.rooms) {
            <mat-chip><mat-icon matChipAvatar>meeting_room</mat-icon>{{ listing.rooms }} Zi.</mat-chip>
          }
          @if (listing.size) {
            <mat-chip><mat-icon matChipAvatar>square_foot</mat-icon>{{ listing.size }}</mat-chip>
          }
          @if (listing.location) {
            <mat-chip><mat-icon matChipAvatar>location_on</mat-icon>{{ listing.location }}</mat-chip>
          }
          <mat-chip><mat-icon matChipAvatar>schedule</mat-icon>{{ age(listing) }}</mat-chip>
        </mat-chip-set>
      </mat-card-content>

      <mat-card-actions align="end">
        <button mat-stroked-button color="warn" (click)="skip.emit()">
          <mat-icon>close</mat-icon> Skip
        </button>
        <button mat-flat-button color="primary" (click)="contacted.emit()">
          <mat-icon>mark_email_read</mat-icon> Messaged
        </button>
      </mat-card-actions>
    </mat-card>
  `,
  styles: [`
    .listing-card { height: 100%; display: flex; flex-direction: column; }
    .title-link { color: inherit; text-decoration: none; }
    .title-link:hover { text-decoration: underline; }
    mat-card-content { flex: 1; padding-top: 8px; }
    mat-card-actions { padding: 8px 16px 16px; }
    .source-subtitle { display: flex; align-items: center; gap: 6px; margin-top: 4px; }
    .source-icon { width: 18px; height: 18px; object-fit: contain; border-radius: 3px; }
  `],
})
export class ListingCardComponent {
  @Input() listing!: Listing;
  @Output() skip = new EventEmitter<void>();
  @Output() contacted = new EventEmitter<void>();

  private static readonly ICON_MAP: Record<string, string> = {
    kleinanzeigen: 'assets/source-icons/kleinanzeigen.ico',
    'wg': 'assets/source-icons/wg-gesucht.ico',
    gag: 'assets/source-icons/gag.ico',
    vonovia: 'assets/source-icons/vonovia.ico',
    'grand': 'assets/source-icons/grandcity.png',
    immowelt: 'assets/source-icons/immowelt.ico',
    wohnsinn: 'assets/source-icons/wohnsinn.png',
    'ohne': 'assets/source-icons/ohne-makler.ico',
  };

  sourceIcon(name: string = ''): string {
    const n = name.trim().toLowerCase();
    for (const [key, path] of Object.entries(ListingCardComponent.ICON_MAP)) {
      if (n.includes(key)) return path;
    }
    return '';
  }

  onIconError(event: Event) {
    (event.target as HTMLImageElement).style.display = 'none';
  }

  age(l: Listing): string {
    const raw = l.published_at || l.first_seen_at;
    if (!raw) return '?';
    try {
      const dt = new Date(raw);
      const h = Math.floor((Date.now() - dt.getTime()) / 3_600_000);
      if (h < 1) return `${Math.floor((Date.now() - dt.getTime()) / 60_000)}m`;
      if (h < 24) return `${h}h`;
      return `${Math.floor(h / 24)}d`;
    } catch {
      return '?';
    }
  }
}
