"""
Immowelt classified-search scraper.

Connects to your real running Chrome via CDP (remote debug port 9222).
This reuses your existing Chrome session, cookies and all — no new browser window.

Before running `fetch`, start Chrome with remote debugging enabled:
  /Applications/Google Chrome.app/Contents/MacOS/Google Chrome --remote-debugging-port=9222

Leave Chrome open while eke fetch runs.
"""

import asyncio
import re
import time
from typing import Any, Dict, List
from urllib.parse import urlencode, urlparse, urlunparse, parse_qs

from utils.browser import OptimizedPlaywrightManager
from utils.performance import PageMetrics, PerformanceTracker

_CARD_SELECTOR = '[data-testid^="classified-card-mfe-"]'
_CDP_URL = "http://localhost:9222"


def _inject_page(url: str, page_num: int) -> str:
    parsed = urlparse(url)
    qs = parse_qs(parsed.query, keep_blank_values=True)
    if page_num > 1:
        qs["page"] = [str(page_num)]
    else:
        qs.pop("page", None)
    new_query = urlencode({k: v[0] for k, v in qs.items()})
    return urlunparse(parsed._replace(query=new_query))


async def _extract_cards(page) -> List[Dict[str, Any]]:
    cards = await page.query_selector_all(_CARD_SELECTOR)
    results = []

    for card in cards:
        try:
            testid = await card.get_attribute("data-testid") or ""
            estate_id = testid.removeprefix("classified-card-mfe-")
            if not estate_id:
                continue

            link_el = await card.query_selector('[data-testid="card-mfe-covering-link-testid"]')
            href = await link_el.get_attribute("href") if link_el else ""
            url = re.sub(r"\?.*", "", href) if href else ""
            if url and not url.startswith("http"):
                url = f"https://www.immowelt.de{url}"

            # Price: "975\xa0€\nWarmmiete"
            price_el = await card.query_selector('[data-testid="cardmfe-price-testid"]')
            price_raw = (await price_el.inner_text()).strip().replace("\xa0", " ") if price_el else ""
            price_match = re.search(r"([\d\s,\.]+)\s*€", price_raw)
            price = price_match.group(1).replace(" ", "").strip() if price_match else ""
            price_type = "Warm" if "Warmmiete" in price_raw else "Kalt" if "Kaltmiete" in price_raw else ""
            if price and price_type:
                price = f"{price} ({price_type})"

            # Keyfacts: "3 Zimmer · 68 m² · 5. Geschoss · frei ab sofort"
            # Clean bullet separators into single line
            keyfacts_el = await card.query_selector('[data-testid="cardmfe-keyfacts-testid"]')
            keyfacts_raw = (await keyfacts_el.inner_text()).strip() if keyfacts_el else ""
            keyfacts = re.sub(r"\s*[·•\·]\s*", " · ", keyfacts_raw.replace("\n", " "))
            keyfacts = re.sub(r"\s+", " ", keyfacts).strip()

            # Extract size from keyfacts: "68 m²" or "70,7 m²"
            size_match = re.search(r"([\d,\.]+)\s*m²", keyfacts)
            size = f"{size_match.group(1)} m²" if size_match else ""

            # Rooms: "3 Zimmer" or "2,5 Zimmer"
            rooms_match = re.match(r"([\d,\.]+)\s*Zimmer", keyfacts)
            rooms_str = rooms_match.group(1).replace(",", ".") if rooms_match else ""

            # Address
            address_el = await card.query_selector('[data-testid="cardmfe-description-box-address"]')
            location = (await address_el.inner_text()).strip() if address_el else ""

            # Title: "3 Zimmer — 68 m²" (location shown separately)
            rooms_label = rooms_match.group(0).strip() if rooms_match else ""
            title_parts = [p for p in [rooms_label, size] if p]
            title = " — ".join(title_parts) if title_parts else location

            # Full card text for blacklist matching at scrape time
            full_text = await card.inner_text()

            results.append({
                "adid": f"imw_{estate_id}",
                "url": url,
                "title": title,
                "price": price,
                "description": full_text,
                "location": location,
                "size": size,
                "rooms": rooms_str,
                "published_at": None,
            })
        except Exception:
            continue

    return results


async def scrape_immowelt(
    browser_manager: OptimizedPlaywrightManager,
    search_url: str,
    max_pages: int = 3,
) -> Dict[str, Any]:
    tracker = PerformanceTracker()
    tracker.start_request()

    all_results: List[Dict] = []
    all_metrics: List[PageMetrics] = []

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
                "performance_metrics": {"pages_requested": 0, "pages_successful": 0, "success_rate": 0, "average_page_time": 0},
            }

        context = browser.contexts[0] if browser.contexts else await browser.new_context()

        for page_num in range(1, max_pages + 1):
            if page_num > 1:
                await asyncio.sleep(3)

            url = _inject_page(search_url, page_num)
            start_time = time.time()

            try:
                page = await context.new_page()
                await page.goto(url, timeout=60000, wait_until="domcontentloaded")

                await page.wait_for_selector(_CARD_SELECTOR, timeout=15000, state="visible")

                cards = await _extract_cards(page)
                await page.close()

                metrics = PageMetrics(
                    page_number=page_num, url=url,
                    start_time=start_time, end_time=time.time(),
                    success=True, retry_count=0, results_count=len(cards),
                )
                all_results.extend(cards)
                all_metrics.append(metrics)
                tracker.add_page_metric(metrics)

                if not cards:
                    break

            except Exception as exc:
                metrics = PageMetrics(
                    page_number=page_num, url=url,
                    start_time=start_time, end_time=time.time(),
                    success=False, retry_count=0,
                    error_message=str(exc), results_count=0,
                )
                all_metrics.append(metrics)
                tracker.add_page_metric(metrics)

        # Do not close browser — it is the user's running Chrome instance

    pages_attempted = len(all_metrics)
    successful = sum(1 for m in all_metrics if m.success)
    request_metrics = tracker.get_request_metrics()

    return {
        "success": True,
        "results": all_results,
        "unique_results": len(all_results),
        "time_taken": round(request_metrics.total_time, 3),
        "performance_metrics": {
            "pages_requested": pages_attempted,
            "pages_successful": successful,
            "success_rate": round((successful / pages_attempted * 100) if pages_attempted else 0, 2),
            "average_page_time": round(request_metrics.to_dict().get("average_page_time", 0), 3),
        },
    }
