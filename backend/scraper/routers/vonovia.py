from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

router = APIRouter()


class VonoviaRequest(BaseModel):
    url: str
    max_pages: int = 3


@router.post("/vonovia-search")
async def vonovia_search(request: Request, body: VonoviaRequest):
    """
    Scrape Vonovia listings from a full search URL.

    Vonovia's listing API requires a client-generated anti-bot token that
    only their own page JS can produce, so this drives the real Chrome
    session (CDP) and reads listings out of the network response the page
    itself triggers, instead of calling the API directly.
    """
    browser_manager = request.app.state.browser_manager
    if not browser_manager:
        raise HTTPException(status_code=503, detail="Service unavailable")

    from scrapers.vonovia import scrape_vonovia

    try:
        result = await scrape_vonovia(search_url=body.url, max_pages=body.max_pages)
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Vonovia scrape failed"))
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
