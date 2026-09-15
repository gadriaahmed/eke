import asyncio
import re
import time
from typing import Any, Dict, List

from utils.performance import PageMetrics, PerformanceTracker

_CDP_URL = "http://localhost:9222"
_CARD_SELECTOR = 'a[href^="/inserat/"]'


async def scrape_wohnsinn(search_url: str) -> Dict[str, Any]:
    tracker = PerformanceTracker()
    tracker.start_request()

    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp(_CDP_URL)
        except Exception as exc:
            return {
                "success": False,
                "results": [],
                "unique_results": 0,
                "time_taken": 0,
                "error": (
                    f"Could not connect to Chrome on {_CDP_URL}: {exc}. "
                    "Start Chrome with: /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222"
                ),
            }

        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        start_time = time.time()
        results = []

        try:
            page = await context.new_page()
            await page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_selector(_CARD_SELECTOR, timeout=15000, state="visible")

            cards = await page.query_selector_all(_CARD_SELECTOR)
            for card in cards:
                try:
                    href = await card.get_attribute("href") or ""
                    adid = href.removeprefix("/inserat/").strip("/")
                    if not adid:
                        continue
                    url = f"https://mieten.wohnsinn.com{href}"
                    text = await card.inner_text()
                    lines = [l.strip() for l in text.splitlines() if l.strip()]

                    # Line structure: Landlord, "Geprüfter Vermieter", "Wohnung in X", Title, "Price · N Zimmer · M m²"
                    title = ""
                    price = ""
                    size = ""
                    rooms = ""
                    location = ""

                    # Last line: "780 € · 3 Zimmer · 65 m²"
                    facts = lines[-1] if lines else ""
                    price_m = re.search(r"([\d,.]+)\s*€", facts)
                    if price_m:
                        price = price_m.group(1)
                    rooms_m = re.search(r"([\d,]+)\s*Zimmer", facts)
                    if rooms_m:
                        rooms = rooms_m.group(1).replace(",", ".")
                    size_m = re.search(r"([\d,]+)\s*m²", facts)
                    if size_m:
                        size = f"{size_m.group(1)} m²"

                    # "Wohnung in Köln" → location
                    for line in lines:
                        if line.startswith("Wohnung in "):
                            location = line.removeprefix("Wohnung in ").strip()
                            break

                    # Title: line before the facts line, skip known boilerplate
                    skip = {"Geprüfter Vermieter", "Wohnung"}
                    for line in reversed(lines[:-1]):
                        if line and not line.startswith("Wohnung in ") and line not in skip:
                            title = line
                            break

                    results.append({
                        "adid": f"ws_{adid}",
                        "url": url,
                        "title": title,
                        "price": price,
                        "description": text,
                        "location": location,
                        "size": size,
                        "rooms": rooms,
                        "published_at": None,
                    })
                except Exception:
                    continue

            await page.close()
        except Exception as exc:
            return {
                "success": False,
                "results": [],
                "unique_results": 0,
                "time_taken": round(time.time() - start_time, 3),
                "error": str(exc),
            }

    return {
        "success": True,
        "results": results,
        "unique_results": len(results),
        "time_taken": round(time.time() - start_time, 3),
    }
