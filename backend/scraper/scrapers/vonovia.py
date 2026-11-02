"""
Vonovia search scraper.

Connects to your real running Chrome via CDP (remote debug port 9222),
same as the Immowelt/Wohnsinn scrapers.

Vonovia's listing API (/api/real-estate/list) requires a client-generated
`x-von-search-token` header that only the page's own JavaScript can
produce, so a plain HTTP request to it gets rejected with 401. Instead of
reverse-engineering that token, this loads the real search page and reads
the listings straight out of the network response the page itself fires.
"""

import asyncio
import time
from typing import Any, Dict, List

_CDP_URL = "http://localhost:9222"
_API_PATH_MARKER = "real-estate/list"
_RESPONSE_WAIT_SECONDS = 8


async def scrape_vonovia(search_url: str, max_pages: int = 3) -> Dict[str, Any]:
    from playwright.async_api import async_playwright

    start_time = time.time()

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
        page = await context.new_page()

        captured: List[Any] = []
        page.on(
            "response",
            lambda resp: captured.append(resp) if _API_PATH_MARKER in resp.url else None,
        )

        results: List[Dict[str, Any]] = []
        seen_ids: set[str] = set()
        total_count: int | None = None

        try:
            await page.goto(search_url, timeout=30000, wait_until="domcontentloaded")

            for page_num in range(max_pages):
                seen_before = len(captured)
                deadline = time.time() + _RESPONSE_WAIT_SECONDS
                while len(captured) == seen_before and time.time() < deadline:
                    await asyncio.sleep(0.2)

                if len(captured) == seen_before:
                    break  # no new listing data arrived — nothing more to page through

                data = await captured[-1].json()

                if total_count is None:
                    total_count = data.get("paging", {}).get("info", {}).get("count")

                new_items = 0
                for item in data.get("results", []):
                    wrk_id = item.get("wrk_id")
                    if not wrk_id or wrk_id in seen_ids:
                        continue
                    seen_ids.add(wrk_id)
                    results.append(item)
                    new_items += 1

                if new_items == 0:
                    break
                if total_count is not None and len(results) >= total_count:
                    break
                if page_num < max_pages - 1:
                    # Trigger the next page: the results list loads more on scroll.
                    await page.mouse.wheel(0, 4000)
                    await page.wait_for_timeout(1000)

        except Exception as exc:
            await page.close()
            return {
                "success": False,
                "results": [],
                "unique_results": 0,
                "time_taken": round(time.time() - start_time, 3),
                "error": str(exc),
            }

        await page.close()

    return {
        "success": True,
        "results": results,
        "unique_results": len(results),
        "time_taken": round(time.time() - start_time, 3),
    }
