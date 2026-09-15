import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Listing {
  adid: string;
  url: string;
  title: string;
  price: string;
  size: string;
  rooms: string;
  location: string;
  published_at: string | null;
  first_seen_at: string;
  search_name: string;
  status: string;
}

export interface FetchSourceResult {
  name: string;
  new: number;
  filtered: number;
  error?: string;
}

export interface FetchResult {
  new: number;
  filtered: number;
  sources?: FetchSourceResult[];
}

@Injectable({ providedIn: 'root' })
export class ListingService {
  constructor(private http: HttpClient) {}

  getListings(status: 'pending' | 'skipped' | 'contacted' = 'pending'): Observable<Listing[]> {
    const path = status === 'pending' ? '/api/listings'
      : status === 'skipped' ? '/api/listings/skipped'
      : '/api/listings/contacted';
    return this.http.get<Listing[]>(path);
  }

  runFetch(): Observable<FetchResult> {
    return this.http.post<FetchResult>('/api/fetch', {});
  }

  skip(adid: string): Observable<unknown> {
    return this.http.post(`/api/listings/${adid}/skip`, {});
  }

  contacted(adid: string): Observable<unknown> {
    return this.http.post(`/api/listings/${adid}/contacted`, {});
  }

  restore(adid: string): Observable<unknown> {
    return this.http.post(`/api/listings/${adid}/pending`, {});
  }
}
