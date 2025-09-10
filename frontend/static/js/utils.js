// Utility functions for location and price formatting

// TODO: Future work - re-enable multi-currency support (INR) 
// Commented out for USD-only implementation - see commit for details
// const USD_TO_INR = 83;

// Price mapping for plans (USD prices in dollars from database)
// NOTE: Prices are now dynamic from backend API
const PRICE_MAP = {
    0: { usd: 0 },           // Freemium
    10: { usd: 10 },         // Starter ($10)
    20: { usd: 20 },         // Pro ($20)
    30: { usd: 30 }          // Ultimate ($30)
    // INR prices commented out for future multi-currency support
    // 10: { inr: 830, usd: 10 },
    // 20: { inr: 1660, usd: 20 },
    // 30: { inr: 2490, usd: 30 }
};

// Get user's location
// TODO: Re-enable location detection for multi-currency support
async function getUserLocation() {
    // Simplified for USD-only implementation
    return { country: 'US', currency: 'USD' };
    
    /* Commented out for future multi-currency support
    try {
        // Try to get from IP geolocation service
        const response = await fetch('https://ipapi.co/json/');
        const data = await response.json();
        return {
            country: data.country_code || 'US',
            currency: data.country_code === 'IN' ? 'INR' : 'USD'
        };
    } catch (error) {
        console.log('Failed to get location, defaulting to US');
        // Fallback to timezone detection
        const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
        if (timezone.includes('Kolkata') || timezone.includes('Asia/Calcutta') || timezone.includes('India')) {
            return { country: 'IN', currency: 'INR' };
        }
        return { country: 'US', currency: 'USD' };
    }
    */
}

// Format price - USD only
// Price is in dollars from database
function formatPrice(priceInDollars, isIndian) {
    // If price is 0, it's free
    if (priceInDollars === 0) {
        return 'Free';
    }
    
    // USD only - ignore isIndian parameter for now
    // Price is already in dollars
    return `$${priceInDollars.toFixed(2)}`;
    
    /* Commented out for future multi-currency support
    // Get the price mapping
    const priceData = PRICE_MAP[priceInCents];
    if (!priceData) {
        // If no mapping exists, convert directly
        if (isIndian) {
            const inrPrice = Math.round(priceInCents * USD_TO_INR / 100);
            return `₹${inrPrice.toLocaleString('en-IN')}`;
        } else {
            return `$${(priceInCents / 100).toFixed(2)}`;
        }
    }
    
    // Use the mapped prices
    if (isIndian) {
        return `₹${priceData.inr.toLocaleString('en-IN')}`;
    } else {
        return `$${(priceData.usd / 100).toFixed(2)}`;
    }
    */
}
