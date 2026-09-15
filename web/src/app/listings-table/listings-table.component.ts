import { Component, Input, Output, EventEmitter } from '@angular/core';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Listing } from '../listing.service';

const SOURCE_ICONS: Record<string, string> = {
  kleinanzeigen: 'assets/source-icons/kleinanzeigen.ico',
  wg: 'assets/source-icons/wg-gesucht.ico',
  gag: 'assets/source-icons/gag.ico',
  vonovia: 'assets/source-icons/vonovia.ico',
  grand: 'assets/source-icons/grandcity.png',
  immowelt: 'assets/source-icons/immowelt.ico',
  wohnsinn: 'assets/source-icons/wohnsinn.png',
  ohne: 'assets/source-icons/ohne-makler.ico',
};

export type ListingAction = 'skip' | 'contacted' | 'restore';

@Component({
  selector: 'app-listings-table',
  standalone: true,
  imports: [MatTableModule, MatButtonModule, MatIconModule, MatChipsModule, MatTooltipModule],
  template: `
    <table mat-table [dataSource]="rows" class="listings-table">

      <ng-container matColumnDef="source">
        <th mat-header-cell *matHeaderCellDef></th>
        <td mat-cell *matCellDef="let row">
          @if (sourceIcon(row.search_name); as icon) {
            <img [src]="icon" [alt]="row.search_name?.trim()" [matTooltip]="row.search_name?.trim()"
                 class="source-icon" (error)="onIconError($event)" />
          }
        </td>
      </ng-container>

      <ng-container matColumnDef="title">
        <th mat-header-cell *matHeaderCellDef>Title</th>
        <td mat-cell *matCellDef="let row" class="title-cell">
          <a [href]="row.url" target="_blank" rel="noopener" class="title-link">{{ row.title || '(no title)' }}</a>
        </td>
      </ng-container>

      <ng-container matColumnDef="price">
        <th mat-header-cell *matHeaderCellDef>Price</th>
        <td mat-cell *matCellDef="let row">
          @if (row.price) {
            <mat-chip-set><mat-chip><mat-icon matChipAvatar>euro</mat-icon>{{ row.price }}</mat-chip></mat-chip-set>
          }
        </td>
      </ng-container>

      <ng-container matColumnDef="rooms">
        <th mat-header-cell *matHeaderCellDef>Rooms</th>
        <td mat-cell *matCellDef="let row">
          @if (row.rooms) {
            <mat-chip-set><mat-chip><mat-icon matChipAvatar>meeting_room</mat-icon>{{ row.rooms }}</mat-chip></mat-chip-set>
          }
        </td>
      </ng-container>

      <ng-container matColumnDef="size">
        <th mat-header-cell *matHeaderCellDef>Size</th>
        <td mat-cell *matCellDef="let row">
          @if (row.size) {
            <mat-chip-set><mat-chip><mat-icon matChipAvatar>square_foot</mat-icon>{{ row.size }}</mat-chip></mat-chip-set>
          }
        </td>
      </ng-container>

      <ng-container matColumnDef="location">
        <th mat-header-cell *matHeaderCellDef>Location</th>
        <td mat-cell *matCellDef="let row" class="location-cell">{{ row.location }}</td>
      </ng-container>

      <ng-container matColumnDef="age">
        <th mat-header-cell *matHeaderCellDef>Age</th>
        <td mat-cell *matCellDef="let row" class="age-cell">{{ age(row) }}</td>
      </ng-container>

      <ng-container matColumnDef="actions">
        <th mat-header-cell *matHeaderCellDef></th>
        <td mat-cell *matCellDef="let row" class="actions-cell">
          @for (btn of actionButtons; track btn.action) {
            @if (btn.style === 'flat') {
              <button mat-flat-button [color]="btn.color" (click)="action.emit({adid: row.adid, action: btn.action})" class="action-btn">
                <mat-icon>{{ btn.icon }}</mat-icon> {{ btn.label }}
              </button>
            } @else {
              <button mat-stroked-button [color]="btn.color" (click)="action.emit({adid: row.adid, action: btn.action})" class="action-btn">
                <mat-icon>{{ btn.icon }}</mat-icon> {{ btn.label }}
              </button>
            }
          }
        </td>
      </ng-container>

      <tr mat-header-row *matHeaderRowDef="columns; sticky: true"></tr>
      <tr mat-row *matRowDef="let row; columns: columns" class="listing-row"></tr>
    </table>
  `,
  styles: [`
    .listings-table { width: 100%; }
    .title-cell { min-width: 260px; max-width: 380px; }
    .title-link { color: inherit; text-decoration: none; line-height: 1.4; }
    .title-link:hover { text-decoration: underline; }
    .location-cell { min-width: 160px; font-size: 13px; opacity: 0.85; }
    .age-cell { white-space: nowrap; font-size: 13px; opacity: 0.7; }
    .actions-cell { white-space: nowrap; }
    .action-btn { margin-right: 6px; }
    .source-icon { width: 20px; height: 20px; object-fit: contain; display: block; }
    mat-chip { font-size: 12px; }
    td.mat-column-source { width: 36px; padding-right: 0; }
    td.mat-column-price, td.mat-column-rooms, td.mat-column-size { white-space: nowrap; }
  `],
})
export class ListingsTableComponent {
  @Input() rows: Listing[] = [];
  @Input() actionButtons: { action: ListingAction; label: string; icon: string; color: string; style: 'flat' | 'stroked' }[] = [];
  @Output() action = new EventEmitter<{ adid: string; action: ListingAction }>();

  columns = ['source', 'title', 'price', 'rooms', 'size', 'location', 'age', 'actions'];

  sourceIcon(name: string = ''): string {
    const n = name.trim().toLowerCase();
    for (const [key, path] of Object.entries(SOURCE_ICONS)) {
      if (n.includes(key)) return path;
    }
    return '';
  }

  onIconError(e: Event) { (e.target as HTMLImageElement).style.display = 'none'; }

  age(l: Listing): string {
    const raw = l.published_at || l.first_seen_at;
    if (!raw) return '?';
    const h = Math.floor((Date.now() - new Date(raw).getTime()) / 3_600_000);
    if (h < 1) return `${Math.floor((Date.now() - new Date(raw).getTime()) / 60_000)}m`;
    if (h < 24) return `${h}h`;
    return `${Math.floor(h / 24)}d`;
  }
}
