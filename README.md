# eke — Apartment Hunt Automator

Fetches new rental listings from multiple German platforms, filters out unwanted ads (swaps, WGs, WBS), and shows them in a terminal table. You open URLs manually to send messages — no automated messaging.

## Sources

| Source | What it scrapes |
|---|---|
| `kleinanzeigen` | ebay-Kleinanzeigen search results |
| `wg-gesucht` | WG-Gesucht apartments/houses |
| `gag` | GAG Köln |
| `vonovia` | Vonovia |
| `grandcity` | Grand City Property |
| `immowelt` | Immowelt (requires Chrome with debug port) |
| `wohnsinn` | Wohnsinn (requires Chrome with debug port + login) |
| `ohne-makler` | Ohne-Makler |

## Requirements

- Python 3.11+
- Node.js (any version — only used for `npm run` shortcuts)
- [uv](https://docs.astral.sh/uv/) (for the API server)
- Google Chrome (for Immowelt and Wohnsinn)

## Setup

Run these **once** after cloning:

```bash
cd ~/Workspace/eke

# Create virtualenv and install eke dependencies
python -m venv .venv
.venv/bin/pip install -r backend/requirements.txt

# Set up the scraper API server
cd backend/scraper
uv sync
uv run playwright install chromium
cd ../..
```

That's it. No need to `source .venv/bin/activate` — the npm scripts invoke `.venv/bin/python` directly, so they work from any terminal without activating the virtualenv first.

## Configuration

Edit `config.yaml` to set your search URLs and preferences:

```yaml
searches:
  - name: "Kleinanzeigen"
    source: kleinanzeigen
    url: "https://www.kleinanzeigen.de/s-wohnung-mieten/koeln/..."
    max_pages: 3

blacklist:
  - tausch    # filters out swap listings
  - WG        # filters out flatshares
  - WBS       # filters out subsidised housing
```

**To change room count or price:** go to the respective website, set your filters, copy the resulting URL, paste it into `config.yaml` under the matching search entry.

Listings matching any blacklist keyword (case-insensitive, checked against title + description) are silently filtered out and never shown.

## Usage

**Terminal 1 — start the API** (keep running):

```bash
npm run be
```

This starts the API server and launches a Chrome instance on port 9222 for Immowelt/Wohnsinn. Your personal Chrome profile is not affected.

**Terminal 2 — fetch and manage listings:**

```bash
npm run fe          # fetch new listings from all sources
npm run list        # show all pending listings
npm run stats       # show counts per status
```

For `done` and `skip`, pass the adid directly to the Python command (npm scripts don't forward arguments cleanly):

```bash
.venv/bin/python -m eke.cli done <adid>
.venv/bin/python -m eke.cli skip <adid>
```

Running `fetch` a second time only shows genuinely new listings — already seen ads are never re-shown.

## Table columns

| Column | Source |
|---|---|
| Title | Listing title |
| Price | Monthly rent (Warm/Kalt where known) |
| Size | Floor area in m² |
| Rooms | Number of rooms (2, 2,5, 3, …) |
| Location | City / district / street |
| Age | Time since listing appeared |
| URL | Open in browser to contact landlord |

## Automation (optional)

Run `fetch` automatically every 20 minutes via cron:

```bash
crontab -e
# Add:
*/20 * * * * cd ~/Workspace/eke/backend && ../.venv/bin/python -m eke.cli fetch >> ../logs/fetch.log 2>&1
```

## Reset

To clear all saved listings and start fresh:

```bash
sqlite3 state.db "DELETE FROM listings; DELETE FROM filter_log;"
```
