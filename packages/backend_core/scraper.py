import httpx
from bs4 import BeautifulSoup
import re
import random
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# --- User-Agent rotation pool ---
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
]

# --- Store-specific selectors (ordered by priority) ---
_STORE_SELECTORS: dict[str, list[str]] = {
    "amazon": [
        "span.a-price span.a-offscreen",
        "#priceblock_ourprice",
        "#priceblock_dealprice",
        "span.a-price-whole",
        "#corePrice_feature_div span.a-offscreen",
        "#price_inside_buybox",
    ],
    "ebay": [
        "span.ux-textspans--BOLD[itemprop='price']",
        "#prcIsum",
        "span.notranslate",
        "div.x-price-primary span.ux-textspans",
    ],
    "walmart": [
        "span[itemprop='price']",
        "span.price-characteristic",
        "[data-testid='price-wrap'] span",
    ],
    "mercadolibre": [
        "span.andes-money-amount__fraction",
        "meta[itemprop='price']",
        ".price-tag-fraction",
    ],
    "aliexpress": [
        ".product-price-value",
        ".uniform-banner-box-price",
        "span.product-price-current",
    ],
    "bestbuy": [
        "div.priceView-customer-price span",
        "div[data-testid='customer-price'] span",
    ],
    "target": [
        "span[data-test='product-price']",
        "[data-test='product-price']",
    ],
}

# --- Generic fallback selectors ---
_GENERIC_SELECTORS = [
    "[data-price]",
    "[itemprop='price']",
    "meta[property='product:price:amount']",
    ".price",
    "#price",
    ".product-price",
    ".current-price",
    ".sale-price",
    ".offer-price",
    ".amount",
    ".price-current",
    ".price__current",
]

# --- Robust price regex ---
_PRICE_REGEX = re.compile(
    r"[\$€£S/\.]?\s?(\d{1,3}(?:[,.\s]\d{3})*(?:[.,]\d{1,2})?)"
)


def _detect_store(url: str) -> str | None:
    """Return a store key if the URL matches a known retailer."""
    domain = urlparse(url).netloc.lower()
    for store in _STORE_SELECTORS:
        if store in domain:
            return store
    return None


def _extract_price_from_text(text: str) -> float | None:
    """Extract the first plausible price number from a string."""
    cleaned = text.strip().replace("\xa0", " ")
    match = _PRICE_REGEX.search(cleaned)
    if match:
        num_str = match.group(1).replace(",", "").replace(" ", "")
        try:
            value = float(num_str)
            if 0.01 <= value <= 999_999:  # sanity bounds
                return value
        except ValueError:
            pass
    return None


async def fetch_price(url: str) -> float | None:
    """
    Extracts a numeric price from a product URL.

    Strategy:
    1. Try store-specific CSS selectors if the domain is recognized.
    2. Fall back to a broad list of generic selectors.
    3. Last resort: scan <meta> tags and visible text for price patterns.
    """
    headers = {
        "User-Agent": random.choice(_USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    try:
        async with httpx.AsyncClient(
            headers=headers, follow_redirects=True, timeout=15.0
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # 1. Store-specific selectors
            store = _detect_store(url)
            if store:
                for selector in _STORE_SELECTORS[store]:
                    el = soup.select_one(selector)
                    if el:
                        # Some elements store the value in content attr (meta tags)
                        raw = el.get("content") or el.get_text()
                        price = _extract_price_from_text(str(raw))
                        if price:
                            return price

            # 2. Generic selectors
            for selector in _GENERIC_SELECTORS:
                el = soup.select_one(selector)
                if el:
                    raw = el.get("content") or el.get("value") or el.get_text()
                    price = _extract_price_from_text(str(raw))
                    if price:
                        return price

            # 3. JSON-LD structured data (schema.org)
            for script in soup.select('script[type="application/ld+json"]'):
                try:
                    import json
                    ld = json.loads(script.string or "")
                    # Handle both single objects and arrays
                    items = ld if isinstance(ld, list) else [ld]
                    for item in items:
                        offers = item.get("offers", item.get("Offers", {}))
                        if isinstance(offers, list):
                            offers = offers[0] if offers else {}
                        p = offers.get("price") or offers.get("lowPrice")
                        if p:
                            return float(p)
                except Exception:
                    continue

            # 4. Last resort: scan visible text
            text_content = soup.get_text(separator=" ")
            price = _extract_price_from_text(text_content)
            if price:
                return price

            logger.warning(f"No price found for {url}")
            return None

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP {e.response.status_code} scraping {url}")
        return None
    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")
        return None
