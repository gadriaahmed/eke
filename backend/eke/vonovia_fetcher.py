from __future__ import annotations

from dataclasses import dataclass

_DETAIL_BASE = "https://www.vonovia.de/zuhause-finden/immobilien"


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


def to_listing(item: dict) -> RawListing:
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
