from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["Pricing"])

@router.get("/prices")
async def get_prices():
    """
    Get dynamic pricing information for all plans.
    Returns prices in dollars (USD).
    """
    # Hard-code USD prices for now; still delivered dynamically.
    return {
        "freemium": 0,       # Free
        "starter": 10,       # $10 - 1 website, text only
        "pro": 20,           # $20 - 1 website + 10 documents  
        "ultimate": 30       # $30 - Multiple websites + 25 documents + voice
    }
