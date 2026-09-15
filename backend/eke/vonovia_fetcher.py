from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode, urlparse, parse_qs

import httpx

from .config import SearchConfig

_API = "https://www.vonovia.de/api/real-estate/list"
_DETAIL_BASE = "https://www.vonovia.de/zuhause-finden/immobilien"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
    "Referer": "https://www.vonovia.de/zuhause-finden",
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
    params = _parse_search_params(search.url)
    results = []
    offset = 0
    limit = 15

    with httpx.Client(headers=_HEADERS, timeout=30) as client:
        while True:
            params["offset"] = str(offset)
            resp = client.get(_API, params=params)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("results", [])
            for item in items:
                results.append(_to_listing(item))
            total = data.get("paging", {}).get("info", {}).get("count", 0)
            offset += limit
            if offset >= total or not items:
                break

    return results


def _parse_search_params(url: str) -> dict:
    qs = parse_qs(urlparse(url).query)
    params: dict = {"orderBy": "date_asc"}
    mapping = {
        "city": "city", "rentType": "rentType", "immoType": "immoType",
        "priceMax": "priceMax", "minRooms": "minRooms", "floor": "floor",
    }
    for src, dst in mapping.items():
        if src in qs:
            params[dst] = qs[src][0]
    return params


def _to_listing(item: dict) -> RawListing:
    adid = f"von_{item['wrk_id']}"
    slug = item.get("slug", "")
    url = f"{_DETAIL_BASE}/{slug}" if slug else _DETAIL_BASE
    title = item.get("titel", "")
    location = f"{item.get('strasse', '')}, {item.get('plz', '')} {item.get('ort', '')}".strip(", ")
    price = f"{item['preis']:.2f}".replace(".", ",") if item.get("preis") else ""
    size = f"{item['groesse']} m²" if item.get("groesse") else ""
    return RawListing(
        adid=adid,
        url=url,
        title=title,
        price=price,
        size=size,
        location=location,
        published_at=None,
        rooms=float(item["anzahl_zimmer"]) if item.get("anzahl_zimmer") else 0.0,
    )
