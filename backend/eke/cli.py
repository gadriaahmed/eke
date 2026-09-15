# Scheduling (macOS):
#   crontab -e
#   */20 * * * * cd ~/Workspace/eke/backend && ../.venv/bin/python -m eke.cli fetch >> ../logs/fetch.log 2>&1

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import typer
from rich.console import Console
from rich.table import Table

from . import config as cfg
from . import db
from . import fetcher
from . import wgg_fetcher
from . import filter as flt

app = typer.Typer(help="Apartment hunt automator (Kleinanzeigen + WG-Gesucht)")


@dataclass
class _Listing:
    adid: str
    url: str
    title: str
    price: str
    description: str
    location: str
    published_at: str | None
    size: str = ""
    rooms: str = ""
console = Console()


def _age(dt_str: str | None) -> str:
    if not dt_str:
        return "?"
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - dt
        h = int(delta.total_seconds() // 3600)
        if h < 1:
            return f"{int(delta.total_seconds() // 60)}m"
        if h < 24:
            return f"{h}h"
        return f"{h // 24}d"
    except Exception:
        return "?"


@app.command()
def fetch(
    sources: str = typer.Option("", help="Comma-separated sources to fetch, e.g. 'immowelt,wohnsinn' (empty = all)"),
) -> None:
    """Fetch new listings from all configured searches."""
    db.init_db()
    try:
        conf = cfg.load()
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[red]Config error:[/red] {e}")
        raise typer.Exit(1)

    allowed = {s.strip() for s in sources.split(",") if s.strip()}

    min_date = db.latest_seen_at()
    # Trim to datetime-only string (drop microseconds and TZ for the API)
    if min_date:
        try:
            dt = datetime.fromisoformat(min_date.replace("Z", "+00:00"))
            min_date = dt.strftime("%Y-%m-%dT%H:%M:%S")
        except Exception:
            min_date = None

    total_new = 0
    total_filtered = 0

    for search in conf.searches:
        if allowed and search.source not in allowed:
            continue
        with console.status(f"Fetching [bold]{search.name}[/bold]…"):
            try:
                if search.source == "wg-gesucht":
                    raw = wgg_fetcher.fetch_search(search)
                    listings = [
                        _Listing(
                            adid=r.adid,
                            url=r.url,
                            title=r.title,
                            price=r.price,
                            description=r.available_from or "",
                            location=r.location,
                            published_at=r.published_at,
                            size=r.size,
                            rooms=fetcher._fmt_rooms(r.rooms),
                        )
                        for r in raw
                    ]
                else:
                    raw_listings = fetcher.fetch_search(conf.api_url, search, min_date)
                    listings = [
                        _Listing(
                            adid=r.adid, url=r.url, title=r.title, price=r.price,
                            description=r.description, location=r.location,
                            published_at=r.published_at, size=r.size, rooms=r.rooms,
                        )
                        for r in raw_listings
                    ]
            except Exception as e:
                console.print(f"[red]  ✗ {search.name}:[/red] {e}")
                continue

        new_count = 0
        filtered_count = 0

        for listing in listings:
            if not listing.adid:
                continue
            if db.already_seen(listing.adid):
                continue

            kw = flt.is_blacklisted(listing.title, listing.description, conf.blacklist)
            if kw:
                db.insert_filter_log(listing.adid, listing.title, kw)
                filtered_count += 1
                continue

            db.insert_listing(
                adid=listing.adid,
                url=listing.url,
                title=listing.title,
                price=listing.price,
                description=listing.description,
                location=listing.location,
                published_at=listing.published_at,
                search_name=search.name,
                size=listing.size,
                rooms=listing.rooms,
            )
            new_count += 1

        total_new += new_count
        total_filtered += filtered_count
        console.print(
            f"  [green]✓[/green] [bold]{search.name}[/bold]: "
            f"{new_count} new, {filtered_count} filtered"
        )

    console.print(
        f"\n[bold]Done.[/bold] {total_new} new listing(s) added, "
        f"{total_filtered} filtered out."
    )

    if total_new:
        console.print()
        _print_pending_table(db.get_pending(), max_rows=total_new)


@app.command(name="list")
def list_pending() -> None:
    """Show all pending listings."""
    db.init_db()
    rows = db.get_pending()
    if not rows:
        console.print("[yellow]No pending listings.[/yellow]")
        return
    _print_pending_table(rows)


@app.command()
def done(adid: str) -> None:
    """Mark a listing as contacted."""
    db.init_db()
    if db.update_status(adid, "contacted"):
        console.print(f"[green]✓[/green] {adid} marked as [bold]contacted[/bold].")
    else:
        console.print(f"[red]Not found:[/red] {adid}")


@app.command()
def skip(adid: str) -> None:
    """Mark a listing as skipped (not relevant)."""
    db.init_db()
    if db.update_status(adid, "skipped"):
        console.print(f"[yellow]✓[/yellow] {adid} marked as [bold]skipped[/bold].")
    else:
        console.print(f"[red]Not found:[/red] {adid}")


@app.command()
def stats() -> None:
    """Show counts per status and last fetch time."""
    db.init_db()
    s = db.stats()
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="bold")
    table.add_column(justify="right")
    table.add_row("Pending", str(s["pending"]))
    table.add_row("Contacted", str(s["contacted"]))
    table.add_row("Skipped", str(s["skipped"]))
    table.add_row("Filtered (blacklist)", str(s["filtered"]))
    table.add_row("Last fetch", s["last_fetch"] or "never")
    console.print(table)


def _print_pending_table(rows: list, max_rows: int | None = None) -> None:
    from rich.table import Column
    table = Table(
        "#",
        Column("Title", max_width=45),
        "Price",
        "Size",
        "Rooms",
        Column("Location", max_width=30),
        "Age",
        Column("URL", no_wrap=True),
        show_lines=True,
        header_style="bold cyan",
    )
    for i, row in enumerate(rows[:max_rows] if max_rows else rows, 1):
        age = _age(row["published_at"] or row["first_seen_at"])
        table.add_row(
            str(i),
            row["title"] or "–",
            row["price"] or "–",
            row["size"] or "–",
            row["rooms"] or "–",
            row["location"] or "–",
            age,
            row["url"],
        )
    console.print(table)


if __name__ == "__main__":
    app()
