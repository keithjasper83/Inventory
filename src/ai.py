import httpx
from src.config import settings
from typing import Optional, Dict, Any, List

class AIClient:
    def __init__(self):
        self.base_url = settings.JARVIS_BASE_URL
        self.health_path = settings.JARVIS_HEALTH_PATH

    async def check_health(self) -> bool:
        if not self.base_url:
            return False
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.base_url}{self.health_path}", timeout=2.0)
                return resp.status_code == 200
        except:
            return False

    async def ocr_image(self, image_bytes: bytes) -> Dict[str, Any]:
        """Perform OCR on an image."""
        if not self.base_url:
            raise ValueError("Jarvis URL not configured")

        async with httpx.AsyncClient() as client:
            files = {'file': image_bytes}
            resp = await client.post(f"{self.base_url}/api/ocr", files=files, timeout=30.0)
            resp.raise_for_status()
            return resp.json()

    async def identify_resistor(self, image_bytes: bytes) -> Dict[str, Any]:
        """Identify resistor from image."""
        if not self.base_url:
             raise ValueError("Jarvis URL not configured")

        async with httpx.AsyncClient() as client:
            files = {'file': image_bytes}
            resp = await client.post(f"{self.base_url}/api/resistor", files=files, timeout=30.0)
            resp.raise_for_status()
            return resp.json()

    async def get_embeddings(self, text: Optional[str] = None, image_bytes: Optional[bytes] = None) -> List[float]:
        """Get embeddings for text or image."""
        if not self.base_url:
             raise ValueError("Jarvis URL not configured")

        async with httpx.AsyncClient() as client:
            if text:
                data = {'text': text}
                resp = await client.post(f"{self.base_url}/api/embeddings", json=data, timeout=10.0)
            elif image_bytes:
                files = {'file': image_bytes}
                resp = await client.post(f"{self.base_url}/api/embeddings", files=files, timeout=10.0)
            else:
                return []

            resp.raise_for_status()
            return resp.json().get('embedding', [])

    async def resolve_url_intent(self, url: str) -> Dict[str, Any]:
        """Resolve URL intent synchronously."""
        if not self.base_url:
             return {"intent": "unknown", "confidence": 0.0}

        async with httpx.AsyncClient() as client:
            data = {'url': url}
            # Catch-all URL resolver: calls Jarvis synchronously
            try:
                resp = await client.post(f"{self.base_url}/api/resolve-url", json=data, timeout=5.0)
                if resp.status_code == 200:
                    return resp.json()
            except Exception as e:
                print(f"Error resolving URL intent: {e}")

            return {"intent": "unknown", "confidence": 0.0}

    async def find_product_url(self, query: str) -> Optional[str]:
        """Find a product page URL based on a search query."""
        if not self.base_url:
            return None

        async with httpx.AsyncClient() as client:
            try:
                data = {'query': query}
                resp = await client.post(f"{self.base_url}/api/search", json=data, timeout=30.0)
                if resp.status_code == 200:
                    results = resp.json().get('results', [])
                    if results:
                        return results[0] # Return first result
            except:
                pass
        return None

    async def scrape_url(self, url: str) -> Dict[str, Any]:
        """Scrape a URL for datasheets and info."""
        if not self.base_url:
             raise ValueError("Jarvis URL not configured")

        async with httpx.AsyncClient() as client:
            data = {'url': url}
            resp = await client.post(f"{self.base_url}/api/scrape", json=data, timeout=60.0)
            resp.raise_for_status()
            return resp.json()

ai_client = AIClient()
