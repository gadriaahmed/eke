from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).parent.parent.parent / "config.yaml"


@dataclass
class SearchConfig:
    name: str
    url: str
    max_pages: int = 3
    source: str = "kleinanzeigen"  # kleinanzeigen | wg-gesucht | immowelt | gag | vonovia | ohne-makler


@dataclass
class Config:
    api_url: str
    searches: list[SearchConfig]
    blacklist: list[str]


def load() -> Config:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"config.yaml not found at {CONFIG_PATH}. "
            "Copy config.yaml.example and fill in your search URLs."
        )
    with CONFIG_PATH.open() as f:
        raw = yaml.safe_load(f)

    searches = [
        SearchConfig(
            name=s["name"],
            url=s["url"],
            max_pages=s.get("max_pages", 3),
            source=s.get("source", "kleinanzeigen"),
        )
        for s in raw.get("searches", [])
    ]
    if not searches:
        raise ValueError("config.yaml must contain at least one search under 'searches'.")

    return Config(
        api_url=raw.get("api_url", "http://localhost:8000").rstrip("/"),
        searches=searches,
        blacklist=[kw.lower() for kw in raw.get("blacklist", [])],
    )
