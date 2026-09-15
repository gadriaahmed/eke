"""
Lightweight web API for the eke frontend.
Run with: .venv/bin/python -m uvicorn web_api:app --port 8001 --reload
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make sure the eke package (and its deps) are importable
sys.path.insert(0, str(Path(__file__).parent))

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from eke import db, fetcher, config as cfg, filter as flt, wgg_fetcher

EXCLUDED_SOURCES = {"immowelt", "wohnsinn"}


@asynccontextmanager
async def _lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="eke web API", version="1.0.0", lifespan=_lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4001"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/listings")
def get_listings():
    rows = db.get_pending()
    return [dict(row) for row in rows]


@app.get("/api/listings/skipped")
def get_skipped():
    rows = db.get_skipped()
    return [dict(row) for row in rows]


@app.get("/api/listings/contacted")
def get_contacted():
    rows = db.get_contacted()
    return [dict(row) for row in rows]


@app.post("/api/listings/{adid}/skip")
def skip_listing(adid: str):
    if not db.update_status(adid, "skipped"):
        raise HTTPException(status_code=404, detail="Listing not found")
    return {"ok": True}


@app.post("/api/listings/{adid}/contacted")
def contacted_listing(adid: str):
    if not db.update_status(adid, "contacted"):
        raise HTTPException(status_code=404, detail="Listing not found")
    return {"ok": True}


@app.post("/api/listings/{adid}/pending")
def restore_listing(adid: str):
    if not db.update_status(adid, "pending"):
        raise HTTPException(status_code=404, detail="Listing not found")
    return {"ok": True}


@app.post("/api/fetch")
def run_fetch():
    try:
        conf = cfg.load()
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=500, detail=str(e))

    min_date = db.latest_seen_at()
    if min_date:
        try:
            dt = datetime.fromisoformat(min_date.replace("Z", "+00:00"))
            min_date = dt.strftime("%Y-%m-%dT%H:%M:%S")
        except Exception:
            min_date = None

    total_new = 0
    total_filtered = 0
    sources: list[dict] = []

    for search in conf.searches:
        if search.source in EXCLUDED_SOURCES:
            continue

        src_new = 0
        src_filtered = 0

        try:
            if search.source == "wg-gesucht":
                raw = wgg_fetcher.fetch_search(search)
                listings = [
                    {
                        "adid": r.adid,
                        "url": r.url,
                        "title": r.title,
                        "price": r.price,
                        "description": r.available_from or "",
                        "location": r.location,
                        "published_at": r.published_at,
                        "size": r.size,
                        "rooms": fetcher._fmt_rooms(r.rooms),
                        "search_name": search.name,
                    }
                    for r in raw
                ]
            else:
                raw_listings = fetcher.fetch_search(conf.api_url, search, min_date)
                listings = [
                    {
                        "adid": r.adid,
                        "url": r.url,
                        "title": r.title,
                        "price": r.price,
                        "description": r.description,
                        "location": r.location,
                        "published_at": r.published_at,
                        "size": r.size,
                        "rooms": r.rooms,
                        "search_name": search.name,
                    }
                    for r in raw_listings
                ]
        except Exception as e:
            sources.append({"name": search.name, "new": 0, "filtered": 0, "error": str(e)})
            continue

        for listing in listings:
            if not listing["adid"]:
                continue
            if db.already_seen(listing["adid"]):
                continue

            kw = flt.is_blacklisted(listing["title"], listing["description"], conf.blacklist)
            if kw:
                db.insert_filter_log(listing["adid"], listing["title"], kw)
                src_filtered += 1
                total_filtered += 1
                continue

            db.insert_listing(
                adid=listing["adid"],
                url=listing["url"],
                title=listing["title"],
                price=listing["price"],
                description=listing["description"],
                location=listing["location"],
                published_at=listing["published_at"],
                search_name=listing["search_name"],
                size=listing["size"],
                rooms=listing["rooms"],
            )
            src_new += 1
            total_new += 1

        sources.append({"name": search.name, "new": src_new, "filtered": src_filtered})

    return {"new": total_new, "filtered": total_filtered, "sources": sources}
