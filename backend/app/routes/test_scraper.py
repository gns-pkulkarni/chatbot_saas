from fastapi import APIRouter, HTTPException
from backend.app.services.scrapper import scrape_website_text
import logging

router = APIRouter(prefix="/test", tags=["Test"])

logger = logging.getLogger(__name__)

@router.get("/scrape")
async def test_scrape(url: str):
    """
    Test endpoint to debug scraping functionality
    """
    try:
        logger.info(f"Test scraping URL: {url}")
        content = await scrape_website_text(url)
        
        return {
            "success": True,
            "url": url,
            "content_length": len(content) if content else 0,
            "content_preview": content[:500] if content else None
        }
    except Exception as e:
        logger.error(f"Test scrape error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        return {
            "success": False,
            "url": url,
            "error": str(e),
            "error_type": type(e).__name__
        }
