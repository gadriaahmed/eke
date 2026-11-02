from __future__ import annotations

from dataclasses import dataclass

import httpx

from .config import SearchConfig


@dataclass
class RawListing:
    adid: str
    url: str
    title: str
    price: str
    description: str
    location: str
    published_at: str | None
    size: str = ""
    rooms: str = ""


def fetch_search(
    api_url: str,
    search: SearchConfig,
    min_publish_date: str | None = None,
) -> list[RawListing]:
    if search.source == "immowelt":
        return _fetch_immowelt(api_url, search)
    if search.source == "wohnsinn":
        return _fetch_wohnsinn(api_url, search)
    if search.source == "gag":
        return _fetch_gag(search)
    if search.source == "vonovia":
        return _fetch_vonovia(api_url, search)
    if search.source == "ohne-makler":
        return _fetch_ohne_makler(search)
    if search.source == "grandcity":
        return _fetch_grandcity(search)
    if search.source == "muenchner-wohnen":
        return _fetch_muenchner_wohnen(api_url, search)
    return _fetch_kleinanzeigen(api_url, search, min_publish_date)


def _fetch_kleinanzeigen(
    api_url: str,
    search: SearchConfig,
    min_publish_date: str | None = None,
) -> list[RawListing]:
    payload: dict = {
        "url": search.url,
        "max_pages": search.max_pages,
    }
    if min_publish_date:
        payload["min_publish_date"] = min_publish_date

    with httpx.Client(timeout=120) as client:
        response = client.post(f"{api_url}/inserate-by-url", json=payload)
        response.raise_for_status()

    return _parse_results(response.json())


def _fetch_immowelt(api_url: str, search: SearchConfig) -> list[RawListing]:
    payload = {"url": search.url, "max_pages": search.max_pages}
    with httpx.Client(timeout=180) as client:
        response = client.post(f"{api_url}/immowelt-search", json=payload)
        response.raise_for_status()
    data = response.json()
    if not data.get("success") or "error" in data:
        raise RuntimeError(data.get("error", "Immowelt scrape failed"))
    return _parse_results(data)


def _fetch_gag(search: SearchConfig) -> list[RawListing]:
    from . import gag_fetcher
    listings = gag_fetcher.fetch_search(search)
    return [
        RawListing(
            adid=r.adid, url=r.url, title=r.title, price=r.price,
            description="", location=r.location, published_at=r.published_at,
            size=r.size, rooms=_fmt_rooms(r.rooms),
        )
        for r in listings
    ]


def _fetch_ohne_makler(search: SearchConfig) -> list[RawListing]:
    from . import ohne_makler_fetcher
    listings = ohne_makler_fetcher.fetch_search(search)
    return [
        RawListing(
            adid=r.adid, url=r.url, title=r.title, price=r.price,
            description="", location=r.location, published_at=r.published_at,
            size=r.size, rooms=_fmt_rooms(r.rooms),
        )
        for r in listings
    ]


def _fetch_vonovia(api_url: str, search: SearchConfig) -> list[RawListing]:
    from . import vonovia_fetcher
    payload = {"url": search.url, "max_pages": search.max_pages}
    with httpx.Client(timeout=90) as client:
        response = client.post(f"{api_url}/vonovia-search", json=payload)
        response.raise_for_status()
    data = response.json()
    if not data.get("success") or "error" in data:
        raise RuntimeError(data.get("error", "Vonovia scrape failed"))
    listings = [vonovia_fetcher.to_listing(item) for item in data.get("results", [])]
    return [
        RawListing(
            adid=r.adid, url=r.url, title=r.title, price=r.price,
            description="", location=r.location, published_at=r.published_at,
            size=r.size, rooms=_fmt_rooms(r.rooms),
        )
        for r in listings
    ]


def _fetch_wohnsinn(api_url: str, search: SearchConfig) -> list[RawListing]:
    payload = {"url": search.url}
    with httpx.Client(timeout=60) as client:
        response = client.post(f"{api_url}/wohnsinn-search", json=payload)
        response.raise_for_status()
    data = response.json()
    if not data.get("success") or "error" in data:
        raise RuntimeError(data.get("error", "Wohnsinn scrape failed"))
    return _parse_results(data)


def _fetch_grandcity(search: SearchConfig) -> list[RawListing]:
    from . import grandcity_fetcher
    listings = grandcity_fetcher.fetch_search(search)
    return [
        RawListing(
            adid=r.adid, url=r.url, title=r.title, price=r.price,
            description="", location=r.location, published_at=r.published_at,
            size=r.size, rooms=_fmt_rooms(r.rooms),
        )
        for r in listings
    ]


def _fetch_muenchner_wohnen(api_url: str, search: SearchConfig) -> list[RawListing]:
    from . import muenchner_wohnen_fetcher
    listings = muenchner_wohnen_fetcher.fetch_search(api_url, search)
    return [
        RawListing(
            adid=r.adid, url=r.url, title=r.title, price=r.price,
            description="", location=r.location, published_at=r.published_at,
            size=r.size, rooms=_fmt_rooms(r.rooms),
        )
        for r in listings
    ]


def _fmt_rooms(val: float | str | None) -> str:
    if not val:
        return ""
    try:
        f = float(str(val).replace(",", "."))
        if f == int(f):
            return str(int(f))
        return str(f).replace(".", ",")
    except (ValueError, TypeError):
        return str(val)


def _parse_results(data: dict) -> list[RawListing]:
    results = []
    for item in data.get("results", []):
        results.append(
            RawListing(
                adid=str(item.get("adid", "")),
                url=item.get("url", ""),
                title=item.get("title", ""),
                price=item.get("price", ""),
                description=item.get("description", ""),
                location=_extract_location(item),
                published_at=item.get("published_at"),
                size=item.get("size", ""),
                rooms=item.get("rooms", ""),
            )
        )
    return results


def _extract_location(item: dict) -> str:
    loc = item.get("location")
    if isinstance(loc, dict):
        return f"{loc.get('zip', '')} {loc.get('city', '')}".strip()
    return str(loc) if loc else ""
