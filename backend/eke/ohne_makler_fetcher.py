from __future__ import annotations

import re
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup

from .config import SearchConfig

BASE = "https://www.ohne-makler.net"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "de-DE,de;q=0.9",
}

# Only keep listings with these room counts (whole and half rooms)
_MIN_ROOMS = 2.5
_MAX_ROOMS = 4.0


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
        resp = client.get(search.url)
        resp.raise_for_status()
    return _parse_page(resp.text)


def _parse_page(html: str) -> list[RawListing]:
    soup = BeautifulSoup(html, "html.parser")
    results = []

    # Each listing card: div.col-span-12 with md:col-span-6 class
    for card in soup.select("div.col-span-12"):
        if "md:col-span-6" not in " ".join(card.get("class", [])):
            continue

        try:
            link = card.select_one('a[href*="/immobilie/"]')
            if not link:
                continue
            href = link.get("href", "")
            url = href if href.startswith("http") else f"{BASE}{href}"
            m = re.search(r"/immobilie/(\d+)/", href)
            if not m:
                continue
            adid = f"om_{m.group(1)}"

            parts = [p.strip() for p in card.get_text("|", strip=True).split("|") if p.strip()]

            # Price: first numeric € value
            price = ""
            for p in parts:
                pm = re.match(r"^([\d.]+(?:,\d+)?)\s*€$", p)
                if pm:
                    price = pm.group(1)
                    break

            # Rooms: standalone number like "3" or "2,5"
            rooms = 0.0
            for p in parts:
                rm = re.match(r"^(\d(?:[,.]\d)?)$", p)
                if rm:
                    try:
                        rooms = float(rm.group(1).replace(",", "."))
                    except ValueError:
                        pass
                    break

            # Filter: skip 1 or 2 room apartments
            if rooms and not (_MIN_ROOMS <= rooms <= _MAX_ROOMS):
                continue

            # Size: "50m²" pattern
            size = ""
            for p in parts:
                sm = re.match(r"^([\d,.]+\s*m²)$", p)
                if sm:
                    size = sm.group(1)
                    break

            # Location: postal code + city pattern "51063 Köln"
            location = ""
            for p in parts:
                if re.match(r"^\d{5}\s+\S", p):
                    location = re.sub(r"\s+", " ", p).strip()
                    break

            # Title: longest text part that isn't price/rooms/size/location
            title = ""
            for p in parts:
                if (len(p) > 10
                        and not re.match(r"^\d{5}", p)
                        and "€" not in p
                        and not re.match(r"^\d(?:[,.]\d)?$", p)
                        and "m²" not in p
                        and "Monatsrate" not in p
                        and "Sortier" not in p
                        and "Karte" not in p):
                    title = p
                    break

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
