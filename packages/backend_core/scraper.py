import httpx
from bs4 import BeautifulSoup
import re
import logging

logger = logging.getLogger(__name__)

async def fetch_price(url: str) -> float | None:
    """
    Extracts a numeric price from a URL using common selectors and regex.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Common selectors for prices
            selectors = [
                '[data-price]', '.price', '#price', '.amount', '.product-price', 
                '.current-price', 'span:contains("$")', 'span:contains("€")'
            ]
            
            # Try specific selectors
            for selector in selectors:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text()
                    # Extract number like 99.99 or 1,250.00
                    match = re.search(r'(\d+[.,]?\d*)', text.replace(',', ''))
                    if match:
                        return float(match.group(1))
            
            # Fallback: search all text for price patterns
            text_content = soup.get_text()
            match = re.search(r'\$\s?(\d+[.,]?\d*)', text_content)
            if match:
                return float(match.group(1))
                
            return None
    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")
        return None
