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

**Terminal 1 — start the backend** (keep running):

```bash
npm run be          # scraper API (port 8000) + Chrome debug port for Immowelt/Wohnsinn
npm run web-api     # web backend (port 8001) — needed only if using the Angular UI
npm run start       # runs all three (be + web-api + ui) concurrently
```

**Terminal 2 — fetch and manage listings:**

```bash
npm run fetch-all   # fetch new listings from all sources
npm run fetch       # fetch only Immowelt and Wohnsinn (Chrome-dependent sources)
npm run list        # show all pending listings in a table
npm run stats       # show counts per status and last fetch time
```

For `done` and `skip`, pass the adid with `--`:

```bash
npm run done -- <adid>   # mark a listing as contacted
npm run skip -- <adid>   # mark a listing as not relevant
```

Running fetch a second time only shows genuinely new listings — already seen ads are never re-shown.

## Table columns

| Column | What it shows |
|---|---|
| Title | Listing title |
| Price | Monthly rent (Warm/Kalt where known) |
| Size | Floor area in m² |
| Rooms | Number of rooms (2, 2,5, 3, …) |
| Location | City / district / street |
| Age | Time since listing appeared |
| URL | Open in browser to contact landlord |

## Automation (optional)

Run `fetch-all` automatically every 20 minutes via cron:

```bash
crontab -e
# Add (replace ~/Workspace/eke with your actual path):
*/20 * * * * cd ~/Workspace/eke/backend && ../.venv/bin/python -m eke.cli fetch >> ../logs/fetch.log 2>&1
```

## Reset

To clear all saved listings and start fresh:

```bash
npm run clear
```
