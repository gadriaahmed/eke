import { Component, OnInit, signal, inject } from '@angular/core';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { ListingService, Listing } from '../listing.service';
import { ListingsTableComponent } from '../listings-table/listings-table.component';

const ACTIONS = [
  { action: 'skip' as const,    label: 'Skip',    icon: 'close', color: 'warn',   style: 'stroked' as const },
  { action: 'restore' as const, label: 'Restore', icon: 'undo',  color: 'accent', style: 'stroked' as const },
];

@Component({
  selector: 'app-contacted-page',
  standalone: true,
  imports: [MatSnackBarModule, ListingsTableComponent],
  template: `
    @if (rows().length === 0) {
      <div class="empty"><p>No messaged listings.</p></div>
    }
    <div class="table-scroll">
      <app-listings-table [rows]="rows()" [actionButtons]="buttons" (action)="onAction($event)"></app-listings-table>
    </div>
  `,
  styles: [`:host { display: flex; flex-direction: column; height: 100%; }`],
})
export class ContactedPageComponent implements OnInit {
  private svc = inject(ListingService);
  private snack = inject(MatSnackBar);

  rows = signal<Listing[]>([]);
  buttons = ACTIONS;

  ngOnInit() { this.reload(); }

  reload() {
    this.svc.getListings('contacted').subscribe({ next: r => this.rows.set(r) });
  }

  onAction(e: { adid: string; action: string }) {
    const row = this.rows().find(r => r.adid === e.adid)!;
    this.rows.update(ls => ls.filter(l => l.adid !== e.adid));
    const call = e.action === 'skip' ? this.svc.skip(e.adid) : this.svc.restore(e.adid);
    call.subscribe({ error: () => { this.rows.update(ls => [row, ...ls]); this.snack.open('Action failed', 'Dismiss', { duration: 3000 }); } });
  }
}
