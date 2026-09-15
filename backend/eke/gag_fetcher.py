from __future__ import annotations

import re
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup

from .config import SearchConfig

BASE = "https://www.gag-koeln.de"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "de-DE,de;q=0.9",
}


@dataclass
class RawListing:
    adid: str
    url: str
    title: str
    price: str
    size: str
    location: str
    published_at: str | None
    rooms: float = 0.0


def fetch_search(search: SearchConfig) -> list[RawListing]:
    with httpx.Client(headers=_HEADERS, timeout=30, follow_redirects=True) as client:
        # Always use the base URL — filter param is client-side only
        resp = client.get(f"{BASE}/immobiliensuche/wohnung-mieten")
        resp.raise_for_status()

    listings = _parse_page(resp.text, search.url)

    # Apply filters from the search config URL
    min_rooms, max_rooms, max_rent = _parse_filter_params(search.url)
    return [l for l in listings if _matches(l, min_rooms, max_rooms, max_rent)]


def _parse_filter_params(url: str) -> tuple[float, float, float]:
    """Extract fromRoom, toRoom, toTotalRent from the filter JSON in the URL."""
    import json, urllib.parse
    min_rooms, max_rooms, max_rent = 0.0, 99.0, 9999.0
    try:
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        if "filter" in qs:
            f = json.loads(qs["filter"][0])
            min_rooms = float(f.get("fromRoom", 0) or 0)
            max_rooms = float(f.get("toRoom", 99) or 99)
            max_rent = float(f.get("toTotalRent", 9999) or 9999)
    except Exception:
        pass
    return min_rooms, max_rooms, max_rent


def _matches(listing: RawListing, min_rooms: float, max_rooms: float, max_rent: float) -> bool:
    if listing.rooms and not (min_rooms <= listing.rooms <= max_rooms):
        return False
    if listing.price and max_rent < 9999:
        try:
            price_val = float(listing.price.replace(".", "").replace(",", "."))
            if price_val > max_rent:
                return False
        except ValueError:
            pass
    return True


def _parse_page(html: str, page_url: str) -> list[RawListing]:
    soup = BeautifulSoup(html, "html.parser")
    results = []

    for card in soup.select("div.appartment"):
        try:
            title_el = card.select_one(".appartment__header")
            title = title_el.get_text(strip=True) if title_el else ""

            addr_el = card.select_one(".appartment__address")
            location = " ".join(addr_el.get_text(" ", strip=True).split()) if addr_el else ""

            price = ""
            size = ""
            rooms = 0.0
            for item in card.select(".appartment__details__item"):
                value_el = item.select_one(".h4")
                label_el = item.select_one("small")
                if not value_el:
                    continue
                value = value_el.get_text(strip=True).replace("\xa0", " ")
                label = label_el.get_text(strip=True).lower() if label_el else ""
                if "miete" in label or "€" in value:
                    price = re.sub(r"\s+", "", value.replace("€", "")).strip()
                elif "wohnfläche" in label or "m²" in value:
                    size = value
                elif "zimmer" in label:
                    try:
                        rooms = float(value.replace(",", "."))
                    except ValueError:
                        pass

            adid = ""
            img = card.select_one("img[data-src]")
            if img:
                m = re.search(r"/OpenImmo/([^/]+)/", img.get("data-src", ""))
                if m:
                    adid = f"gag_{m.group(1)}"
            if not adid:
                adid = f"gag_{abs(hash(title + location)) % 10**10}"

            link_el = card.select_one("a[href]")
            url = ""
            if link_el:
                href = link_el.get("href", "")
                url = href if href.startswith("http") else f"{BASE}{href}"
            if not url:
                url = page_url

            if not title and not price:
                continue

            results.append(RawListing(
                adid=adid,
                url=url,
                title=title,
                price=price,
                size=size,
                location=location,
                published_at=None,
                rooms=rooms,
            ))
        except Exception:
            continue

    return results
