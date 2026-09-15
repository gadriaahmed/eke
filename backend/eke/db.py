import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "state.db"


@contextmanager
def _conn():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db() -> None:
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS listings (
                adid             TEXT PRIMARY KEY,
                url              TEXT NOT NULL,
                title            TEXT,
                price            TEXT,
                description      TEXT,
                location         TEXT,
                size             TEXT,
                rooms            TEXT,
                published_at     TEXT,
                first_seen_at    TEXT NOT NULL,
                status           TEXT NOT NULL DEFAULT 'pending',
                status_updated_at TEXT,
                search_name      TEXT
            );

            CREATE TABLE IF NOT EXISTS filter_log (
                adid             TEXT PRIMARY KEY,
                title            TEXT,
                matched_keyword  TEXT,
                filtered_at      TEXT NOT NULL
            );
        """)
    # migrate existing DBs that don't have the size/rooms columns yet
    with _conn() as con:
        for col in ("size TEXT", "rooms TEXT"):
            try:
                con.execute(f"ALTER TABLE listings ADD COLUMN {col}")
            except Exception:
                pass


def already_seen(adid: str) -> bool:
    with _conn() as con:
        row = con.execute("SELECT 1 FROM listings WHERE adid = ?", (adid,)).fetchone()
        if row:
            return True
        row = con.execute("SELECT 1 FROM filter_log WHERE adid = ?", (adid,)).fetchone()
        return row is not None


def insert_listing(
    adid: str,
    url: str,
    title: str,
    price: str,
    description: str,
    location: str,
    published_at: str | None,
    search_name: str,
    size: str = "",
    rooms: str = "",
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as con:
        con.execute(
            """
            INSERT OR IGNORE INTO listings
                (adid, url, title, price, description, location, size, rooms, published_at, first_seen_at, search_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (adid, url, title, price, description, location, size, rooms, published_at, now, search_name),
        )


def insert_filter_log(adid: str, title: str, matched_keyword: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as con:
        con.execute(
            "INSERT OR IGNORE INTO filter_log (adid, title, matched_keyword, filtered_at) VALUES (?, ?, ?, ?)",
            (adid, title, matched_keyword, now),
        )


def update_status(adid: str, status: str) -> bool:
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as con:
        cur = con.execute(
            "UPDATE listings SET status = ?, status_updated_at = ? WHERE adid = ?",
            (status, now, adid),
        )
        return cur.rowcount > 0


def get_pending() -> list[sqlite3.Row]:
    return _get_by_status("pending")


def get_skipped() -> list[sqlite3.Row]:
    return _get_by_status("skipped")


def get_contacted() -> list[sqlite3.Row]:
    return _get_by_status("contacted")


def _get_by_status(status: str) -> list[sqlite3.Row]:
    with _conn() as con:
        return con.execute(
            """
            SELECT adid, url, title, price, size, rooms, location, published_at, first_seen_at, search_name, status
            FROM listings
            WHERE status = ?
            ORDER BY first_seen_at DESC
            """,
            (status,),
        ).fetchall()


def latest_seen_at() -> str | None:
    """Return the most recent first_seen_at across all listings, or None."""
    with _conn() as con:
        row = con.execute("SELECT MAX(first_seen_at) FROM listings").fetchone()
        return row[0] if row else None


def stats() -> dict:
    with _conn() as con:
        counts = {
            row["status"]: row["cnt"]
            for row in con.execute(
                "SELECT status, COUNT(*) as cnt FROM listings GROUP BY status"
            ).fetchall()
        }
        filtered = con.execute("SELECT COUNT(*) FROM filter_log").fetchone()[0]
        last_fetch = con.execute("SELECT MAX(first_seen_at) FROM listings").fetchone()[0]
    return {
        "pending": counts.get("pending", 0),
        "contacted": counts.get("contacted", 0),
        "skipped": counts.get("skipped", 0),
        "filtered": filtered,
        "last_fetch": last_fetch,
    }
