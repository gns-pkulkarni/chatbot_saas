import sys

if sys.platform == "win32":
    from crawl4ai.utils import configure_windows_event_loop
    configure_windows_event_loop()

import asyncio
from crawl4ai import AsyncWebCrawler

async def scrape_website_text(url: str) -> str:
    """
    Scrape website content using crawl4ai
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Starting to scrape URL: {url}")
        async with AsyncWebCrawler() as crawler:
            logger.debug("Crawler initialized")
            result = await crawler.arun(
                url=url,
                deep_crawl="bfs",  # breadth-first search
                max_pages=20,  # increase as needed
                max_depth=3,  # increase if needed
                timeout=30
            )
            logger.debug(f"Scraping result: {result}")
            
            if result and result.markdown:
                content = result.markdown.raw_markdown
                logger.info(f"Successfully scraped {len(content)} characters")
                return content
            else:
                logger.warning("No markdown content found in result")
                return ""
    except Exception as e:
        logger.error(f"Error scraping {url}: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(traceback.format_exc())
        raise  # Re-raise the exception instead of returning empty string

def scrape_website_text_sync(url: str) -> str:
    """
    Synchronous wrapper for the async scrape function
    """
    # Check if we're already in an event loop
    try:
        loop = asyncio.get_running_loop()
        # If we're in a loop, create a new thread to run the async function
        import concurrent.futures
        import functools
        
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, scrape_website_text(url))
            return future.result()
    except RuntimeError:
        # No event loop running, we can use asyncio.run directly
        return asyncio.run(scrape_website_text(url))
