import pytest
import httpx
from unittest.mock import patch, MagicMock, AsyncMock
from src.ai import ai_client, AIClient
from src.config import settings

@pytest.mark.asyncio
@patch("src.ai.httpx.AsyncClient")
async def test_resolve_url_intent_exception_handling(mock_client_class):
    # Ensure that the base_url is set so the if statement doesn't return early
    ai_client.base_url = "http://test-jarvis.com"

    # Setup mock to throw an exception on post
    mock_client = AsyncMock()
    mock_client_class.return_value.__aenter__.return_value = mock_client
    mock_client.post.side_effect = Exception("Simulated connection error")

    # Call the function
    result = await ai_client.resolve_url_intent("http://example.com")

    # Verify fallback is returned correctly
    assert result == {"intent": "unknown", "confidence": 0.0}

    # Also verify that the URL was used correctly
    mock_client.post.assert_called_once()
    args, kwargs = mock_client.post.call_args
    assert "url" in kwargs.get("json", {})
    assert kwargs["json"]["url"] == "http://example.com"
