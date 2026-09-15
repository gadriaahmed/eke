from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

router = APIRouter()


class ImmoweltRequest(BaseModel):
    url: str
    max_pages: int = 3


@router.post("/immowelt-search")
async def immowelt_search(request: Request, body: ImmoweltRequest):
    """
    Scrape Immowelt classified listings from a full search URL.
    Requires HEADLESS=false (Cloudflare blocks headless browsers).
    """
    browser_manager = request.app.state.browser_manager
    if not browser_manager:
        raise HTTPException(status_code=503, detail="Service unavailable")

    from scrapers.immowelt import scrape_immowelt

    try:
        return await scrape_immowelt(
            browser_manager=browser_manager,
            search_url=body.url,
            max_pages=body.max_pages,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
