import httpx
import json
import hashlib
import time
from src.config import settings
from typing import Optional, Dict, Any, List, Tuple
import logging

logger = logging.getLogger(__name__)

class AIClient:
    def __init__(self):
        self.base_url = settings.JARVIS_BASE_URL
        self.health_path = settings.JARVIS_HEALTH_PATH
        self._cache: Dict[str, Tuple[float, Any]] = {}
        self.cache_ttl = 86400  # 24 hours

    def _get_cache_key(self, prefix: str, data: Any) -> str:
        """Generate a deterministic cache key for AI queries."""
        if isinstance(data, bytes):
            hash_str = hashlib.md5(data).hexdigest()
        else:
            hash_str = hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()
        return f"{prefix}:{hash_str}"

    async def _get_cached_response(self, cache_key: str) -> Optional[Any]:
        if cache_key in self._cache:
            timestamp, data = self._cache[cache_key]
            if time.time() - timestamp <= self.cache_ttl:
                return data
            else:
                # Expired
                del self._cache[cache_key]
        return None

    async def _set_cached_response(self, cache_key: str, data: Any):
        # Manage cache size to prevent memory leaks in long-running processes
        if len(self._cache) > 1000:
            # Simple eviction: clear cache when too large
            self._cache.clear()
        self._cache[cache_key] = (time.time(), data)

    async def _make_request(
        self, method: str, path: str, timeout: float,
        fallback: Any = None, **kwargs
    ) -> Any:
        """
        Unified wrapper for AI service calls.
        Handles missing base URL, network errors, and returns a graceful fallback.
        """
        if not self.base_url:
            if fallback is not None:
                return fallback
            raise ValueError("Jarvis URL not configured")

        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.request(method, url, timeout=timeout, **kwargs)
                resp.raise_for_status()
                # Consider standard JSON response where applicable, but check_health returns bool
                if "application/json" in resp.headers.get("content-type", ""):
                    return resp.json()
                # If not JSON, but expected a dict due to fallback type matching
                if isinstance(fallback, dict):
                    return fallback
                return resp.status_code == 200
        except httpx.HTTPError as e:
            logger.error(f"HTTP Error calling AI Service {path}: {e}")
            if fallback is not None:
                return fallback
            raise
        except Exception as e:
            logger.error(f"Unexpected error calling AI Service {path}: {e}")
            if fallback is not None:
                return fallback
            raise

    async def check_health(self) -> bool:
        if not self.base_url:
            return False
        res = await self._make_request("GET", self.health_path, timeout=2.0, fallback=False)
        # _make_request will return True/False or fallback
        return bool(res)

    async def ocr_image(self, image_bytes: bytes) -> Dict[str, Any]:
        """Perform OCR on an image."""
        files = {'file': image_bytes}
        return await self._make_request("POST", "/api/ocr", timeout=30.0, fallback={}, files=files)

    async def identify_resistor(self, image_bytes: bytes) -> Dict[str, Any]:
        """Identify resistor from image."""
        files = {'file': image_bytes}
        return await self._make_request("POST", "/api/resistor", timeout=30.0, fallback={}, files=files)

    async def count_resistors_bulk(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Count and identify multiple resistors from a single image.
        """
        files = {'file': image_bytes}
        # Provide empty structure for graceful degradation
        fallback = {
            "resistors": [],
            "total_count": 0,
            "failed_count": 0,
            "grouped": {}
        }
        return await self._make_request(
            "POST", "/api/resistor/bulk-count",
            timeout=120.0, fallback=fallback, files=files
        )

    async def get_embeddings(self, text: Optional[str] = None, image_bytes: Optional[bytes] = None) -> List[float]:
        """Get embeddings for text or image."""
        cache_key = None
        if text:
            cache_key = self._get_cache_key("emb", text)
            data = {'text': text}
            cached = await self._get_cached_response(cache_key)
            if cached: return cached
            res = await self._make_request("POST", "/api/embeddings", timeout=10.0, fallback={}, json=data)
        elif image_bytes:
            cache_key = self._get_cache_key("emb", image_bytes)
            files = {'file': image_bytes}
            cached = await self._get_cached_response(cache_key)
            if cached: return cached
            res = await self._make_request("POST", "/api/embeddings", timeout=10.0, fallback={}, files=files)
        else:
            return []

        if isinstance(res, dict):
            embedding = res.get('embedding', [])
            if embedding and cache_key:
                await self._set_cached_response(cache_key, embedding)
            return embedding
        return []

    async def resolve_url_intent(self, url: str) -> Dict[str, Any]:
        """Resolve URL intent synchronously."""
        data = {'url': url}
        fallback = {"intent": "unknown", "confidence": 0.0}

        cache_key = self._get_cache_key("intent", url)
        cached = await self._get_cached_response(cache_key)
        if cached: return cached

        res = await self._make_request("POST", "/api/resolve-url", timeout=5.0, fallback=fallback, json=data)
        # Handle cases where _make_request doesn't return dict fallback
        if isinstance(res, dict) and "intent" in res:
            if res.get("intent") != "unknown":
                await self._set_cached_response(cache_key, res)
            return res
        return fallback

    async def find_product_url(self, query: str) -> Optional[str]:
        """Find a product page URL based on a search query."""
        data = {'query': query}
        cache_key = self._get_cache_key("search", query)
        cached = await self._get_cached_response(cache_key)
        if cached: return cached.get("url")

        res = await self._make_request("POST", "/api/search", timeout=30.0, fallback={}, json=data)

        if isinstance(res, dict):
            results = res.get('results', [])
            if results:
                await self._set_cached_response(cache_key, {"url": results[0]})
                return results[0]
        return None

    async def scrape_url(self, url: str) -> Dict[str, Any]:
        """Scrape a URL for datasheets and info."""
        data = {'url': url}
        cache_key = self._get_cache_key("scrape", url)
        cached = await self._get_cached_response(cache_key)
        if cached: return cached

        res = await self._make_request("POST", "/api/scrape", timeout=60.0, fallback={}, json=data)
        if res and isinstance(res, dict):
            await self._set_cached_response(cache_key, res)
            return res
        return {}

ai_client = AIClient()
