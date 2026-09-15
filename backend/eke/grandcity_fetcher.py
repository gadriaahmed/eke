from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse, parse_qs

import httpx
from bs4 import BeautifulSoup

from .config import SearchConfig

BASE = "https://www.grandcityproperty.de"

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
    rooms: float
    location: str
    published_at: str | None


def fetch_search(search: SearchConfig) -> list[RawListing]:
    city_filter = _parse_city(search.url)
    with httpx.Client(headers=_HEADERS, timeout=30, follow_redirects=True) as client:
        resp = client.get(search.url)
        resp.raise_for_status()
    return _parse_page(resp.text, city_filter)


def _parse_city(url: str) -> str:
    qs = parse_qs(urlparse(url).query)
    return (qs.get("city", [""])[0] or qs.get("cityField", [""])[0]).strip().lower()


def _parse_page(html: str, city_filter: str) -> list[RawListing]:
    soup = BeautifulSoup(html, "html.parser")
    results = []

    for card in soup.select("div.real-estate-item"):
        try:
            adid = card.get("data-id", "")
            if not adid:
                continue

            # Filter by city — server ignores the city param
            card_city = (card.get("data-city") or "").strip().lower()
            if city_filter and card_city != city_filter:
                continue

            adid = f"gcp_{adid}"

            nice_url = (card.get("data-nice-url") or "").strip()
            url = f"{BASE}{nice_url}" if nice_url else BASE

            title = (card.get("data-title") or "").strip()
            price = (card.get("data-price") or "").strip()

            # img alt gives full "Street, PLZ City"
            img = card.select_one("img[alt]")
            location = " ".join((img.get("alt") or "").split()) if img else ""
            if not location:
                street = (card.get("data-street") or "").replace("-", " ").strip()
                city = (card.get("data-city") or "").strip()
                location = f"{street}, {city}".strip(", ")

            # Parse size and rooms from sequential text parts:
            # "Fläche | 65 m | 2 | Zimmer | 4 | Stock | 0"
            text_parts = [p.strip() for p in card.get_text("|", strip=True).split("|") if p.strip()]
            size = ""
            rooms = 0.0
            for i, p in enumerate(text_parts):
                if p == "Fläche" and i + 1 < len(text_parts):
                    raw = text_parts[i + 1].rstrip("m").strip()
                    size = f"{raw} m²"
                elif p == "Zimmer" and i + 1 < len(text_parts):
                    try:
                        rooms = float(text_parts[i + 1].replace(",", "."))
                    except ValueError:
                        pass

            if not title and not price:
                continue

            results.append(RawListing(
                adid=adid,
                url=url,
                title=title,
                price=price,
                size=size,
                rooms=rooms,
                location=location,
                published_at=None,
            ))
        except Exception:
            continue

    return results
