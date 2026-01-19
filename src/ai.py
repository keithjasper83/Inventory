import httpx
from src.config import settings
from src.logging_config import get_logger
from typing import Optional, Dict, Any, List

logger = get_logger(__name__)


class AIClient:
    """Client for AI services hosted on Jarvis."""
    
    def __init__(self):
        self.base_url = settings.JARVIS_BASE_URL
        self.health_path = settings.JARVIS_HEALTH_PATH

    async def check_health(self) -> bool:
        """Check if AI service is available."""
        if not self.base_url:
            logger.warning("Jarvis base URL not configured")
            return False
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.base_url}{self.health_path}", timeout=2.0)
                is_healthy = resp.status_code == 200
                logger.info(f"AI health check: {'healthy' if is_healthy else 'unhealthy'}")
                return is_healthy
        except Exception as e:
            logger.error(f"AI health check failed: {e}")
            return False

    async def ocr_image(self, image_bytes: bytes) -> Dict[str, Any]:
        """Perform OCR on an image."""
        if not self.base_url:
            logger.error("Jarvis URL not configured for OCR")
            raise ValueError("Jarvis URL not configured")

        try:
            async with httpx.AsyncClient() as client:
                files = {'file': image_bytes}
                resp = await client.post(f"{self.base_url}/api/ocr", files=files, timeout=30.0)
                resp.raise_for_status()
                result = resp.json()
                logger.info(f"OCR completed with confidence: {result.get('confidence', 0)}")
                return result
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            raise

    async def identify_resistor(self, image_bytes: bytes) -> Dict[str, Any]:
        """Identify resistor from image."""
        if not self.base_url:
            logger.error("Jarvis URL not configured for resistor identification")
            raise ValueError("Jarvis URL not configured")

        try:
            async with httpx.AsyncClient() as client:
                files = {'file': image_bytes}
                resp = await client.post(f"{self.base_url}/api/resistor", files=files, timeout=30.0)
                resp.raise_for_status()
                result = resp.json()
                logger.info(f"Resistor identification completed: {result.get('is_resistor', False)}")
                return result
        except Exception as e:
            logger.error(f"Resistor identification failed: {e}")
            raise

    async def get_embeddings(self, text: Optional[str] = None, image_bytes: Optional[bytes] = None) -> List[float]:
        """Get embeddings for text or image."""
        if not self.base_url:
            logger.error("Jarvis URL not configured for embeddings")
            raise ValueError("Jarvis URL not configured")

        try:
            async with httpx.AsyncClient() as client:
                if text:
                    data = {'text': text}
                    resp = await client.post(f"{self.base_url}/api/embeddings", json=data, timeout=10.0)
                elif image_bytes:
                    files = {'file': image_bytes}
                    resp = await client.post(f"{self.base_url}/api/embeddings", files=files, timeout=10.0)
                else:
                    logger.warning("No text or image provided for embeddings")
                    return []

                resp.raise_for_status()
                result = resp.json().get('embedding', [])
                logger.info(f"Generated embeddings with {len(result)} dimensions")
                return result
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise

    async def resolve_url_intent(self, url: str) -> Dict[str, Any]:
        """Resolve URL intent synchronously."""
        if not self.base_url:
            logger.warning("Jarvis URL not configured for URL resolution")
            return {"intent": "unknown", "confidence": 0.0}

        try:
            async with httpx.AsyncClient() as client:
                data = {'url': url}
                resp = await client.post(f"{self.base_url}/api/resolve-url", json=data, timeout=5.0)
                if resp.status_code == 200:
                    result = resp.json()
                    logger.info(f"URL intent resolved: {result.get('intent', 'unknown')}, confidence: {result.get('confidence', 0)}")
                    return result
        except Exception as e:
            logger.error(f"URL intent resolution failed: {e}")

        return {"intent": "unknown", "confidence": 0.0}

    async def find_product_url(self, query: str) -> Optional[str]:
        """Find a product page URL based on a search query."""
        if not self.base_url:
            logger.warning("Jarvis URL not configured for product search")
            return None

        try:
            async with httpx.AsyncClient() as client:
                data = {'query': query}
                resp = await client.post(f"{self.base_url}/api/search", json=data, timeout=30.0)
                if resp.status_code == 200:
                    results = resp.json().get('results', [])
                    if results:
                        logger.info(f"Found product URL for query: {query}")
                        return results[0]
        except Exception as e:
            logger.error(f"Product search failed for query '{query}': {e}")
        
        return None

    async def scrape_url(self, url: str) -> Dict[str, Any]:
        """Scrape a URL for datasheets and info."""
        if not self.base_url:
            logger.error("Jarvis URL not configured for scraping")
            raise ValueError("Jarvis URL not configured")

        try:
            async with httpx.AsyncClient() as client:
                data = {'url': url}
                resp = await client.post(f"{self.base_url}/api/scrape", json=data, timeout=60.0)
                resp.raise_for_status()
                result = resp.json()
                logger.info(f"Scraped URL: {url}, found {len(result.get('datasheets', []))} datasheets")
                return result
        except Exception as e:
            logger.error(f"Scraping failed for URL '{url}': {e}")
            raise

ai_client = AIClient()
