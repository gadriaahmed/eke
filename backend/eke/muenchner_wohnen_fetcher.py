from __future__ import annotations

from dataclasses import dataclass

from .config import SearchConfig

# Münchner Wohnen GmbH (merger of GEWOFAG + GWG München) is Munich's municipal
# housing company -- the equivalent of GAG in Köln. Unlike GAG, it has no public
# search of its own: ~90% of its stock is allocated via the city's SOWON waitlist,
# and the remaining free-market listings are published on Immowelt and ImmoScout24
# under its company profile instead.
#
# ImmoScout24 is behind an aggressive bot-protection wall that blocks even the
# Chrome-CDP approach used for Immowelt, so this source rides on the existing
# Immowelt scraper (see immowelt router / scraper) against a broad Munich search
# and keeps only cards that mention Münchner Wohnen (or its predecessor names).

_NAME_MARKERS = (
    "münchner wohnen",
    "muenchner wohnen",
    "gewofag",
    "gwg münchen",
    "gwg muenchen",
)


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


def fetch_search(api_url: str, search: SearchConfig) -> list[RawListing]:
    from . import fetcher as base_fetcher

    raw_listings = base_fetcher._fetch_immowelt(api_url, search)
    return [
        RawListing(
            adid=r.adid,
            url=r.url,
            title=r.title,
            price=r.price,
            size=r.size,
            location=r.location,
            published_at=r.published_at,
            rooms=_to_float(r.rooms),
        )
        for r in raw_listings
        if _mentions_muenchner_wohnen(r.title, r.description)
    ]


def _mentions_muenchner_wohnen(title: str, description: str) -> bool:
    text = f"{title} {description}".lower()
    return any(marker in text for marker in _NAME_MARKERS)


def _to_float(val: str | float | None) -> float:
    if not val:
        return 0.0
    try:
        return float(str(val).replace(",", "."))
    except ValueError:
        return 0.0
