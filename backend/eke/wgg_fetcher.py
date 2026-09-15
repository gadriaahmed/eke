from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import httpx
from bs4 import BeautifulSoup

from .config import SearchConfig

BASE = "https://www.wg-gesucht.de"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
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
    available_from: str | None
    published_at: str | None
    rooms: float = 0.0


def fetch_search(search: SearchConfig) -> list[RawListing]:
    """Scrape WG-Gesucht listing pages directly (no intermediate API needed)."""
    base_url = search.url.rstrip("/")
    results: list[RawListing] = []

    with httpx.Client(headers=_HEADERS, timeout=30, follow_redirects=True) as client:
        for page in range(search.max_pages):
            url = _page_url(base_url, page)
            resp = client.get(url)
            resp.raise_for_status()
            listings = _parse_page(resp.text)
            if not listings:
                break
            results.extend(listings)
            if page < search.max_pages - 1:
                time.sleep(2)

    return results


def _page_url(base_url: str, page: int) -> str:
    new_url = re.sub(r"(\.\d+)\.html$", f".{page}.html", base_url)
    if page > 0:
        new_url += "?pagination=1"
    return new_url


def _parse_online(text: str) -> str | None:
    """Parse 'Online: X' text into an ISO 8601 UTC timestamp."""
    text = text.strip()
    now = datetime.now(timezone.utc)

    # DD.MM.YYYY
    m = re.match(r"(\d{2})\.(\d{2})\.(\d{4})", text)
    if m:
        try:
            dt = datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)), tzinfo=timezone.utc)
            return dt.isoformat()
        except ValueError:
            return None

    # N Minuten
    m = re.match(r"(\d+)\s+Minuten?", text)
    if m:
        return (now - timedelta(minutes=int(m.group(1)))).isoformat()

    # 1 Stunde / N Stunden
    m = re.match(r"(\d+)\s+Stunden?", text)
    if m:
        return (now - timedelta(hours=int(m.group(1)))).isoformat()

    return None


def _parse_page(html: str) -> list[RawListing]:
    soup = BeautifulSoup(html, "html.parser")
    results = []

    for card in soup.select("div.wgg_card.offer_list_item"):
        adid = card.get("data-id", "")
        if not adid:
            continue

        if "deactivated" in card.get("class", []):
            continue

        title_tag = card.select_one("h2.truncate_title a")
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)
        href = title_tag.get("href", "")
        url = href if href.startswith("http") else f"{BASE}{href}"

        middle = card.select_one("div.row.middle")
        price = ""
        size = ""
        available_from = None
        if middle:
            cols = middle.select("div[class*='col-xs']")
            if len(cols) >= 1:
                price = cols[0].get_text(strip=True).replace("€", "").replace("€", "").strip()
            if len(cols) >= 2:
                available_from = cols[1].get_text(strip=True) or None
            if len(cols) >= 3:
                size = cols[2].get_text(strip=True)

        # Rooms: parse from title e.g. "3-Zimmer-Wohnung" or "2,5-Zimmer"
        rooms = 0.0

        location = ""
        loc_span = card.select_one("div.col-xs-11 span")
        if loc_span:
            raw_loc = loc_span.get_text("|", strip=True)
            # Parts: "2-Zimmer-Wohnung | Köln Eil | Ebereschenweg"
            parts = [" ".join(p.split()) for p in raw_loc.split("|") if p.strip()]
            if len(parts) >= 2:
                location = ", ".join(parts[1:])
            elif parts:
                location = parts[0]
            # Rooms from first part: "2-Zimmer-Wohnung" or "3,5-Zimmer"
            if parts:
                rm = re.match(r"^(\d(?:[,.]\d)?)-Zimmer", parts[0])
                if rm:
                    try:
                        rooms = float(rm.group(1).replace(",", "."))
                    except ValueError:
                        pass

        # "Online: 20 Minuten" / "Online: 3 Stunden" / "Online: 22.06.2026"
        published_at = None
        online_span = card.find("span", string=re.compile(r"Online:"))
        if online_span:
            online_text = online_span.get_text(strip=True).removeprefix("Online:").strip()
            published_at = _parse_online(online_text)

        results.append(
            RawListing(
                adid=f"wgg_{adid}",
                url=url,
                title=title,
                price=price,
                size=size,
                location=location,
                available_from=available_from,
                published_at=published_at,
                rooms=rooms,
            )
        )

    return results
