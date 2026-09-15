from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

router = APIRouter()


class WohnsinnRequest(BaseModel):
    url: str


@router.post("/wohnsinn-search")
async def wohnsinn_search(request: Request, body: WohnsinnRequest):
    from scrapers.wohnsinn import scrape_wohnsinn
    try:
        result = await scrape_wohnsinn(search_url=body.url)
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Wohnsinn scrape failed"))
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
