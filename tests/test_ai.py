import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.ai import AIClient, ai_client


def test_ocr_image_success():
    client = AIClient()
    client.base_url = "http://fake-url"

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"text": "Hello World"}
    mock_resp.raise_for_status = MagicMock()

    mock_post = AsyncMock(return_value=mock_resp)

    with patch("httpx.AsyncClient.post", mock_post):
        result = asyncio.run(client.ocr_image(b"fake_image_bytes"))

    assert result == {"text": "Hello World"}
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert args[0] == "http://fake-url/api/ocr"
    assert kwargs["files"] == {"file": b"fake_image_bytes"}
    assert kwargs["timeout"] == 30.0


def test_ocr_image_missing_url():
    client = AIClient()
    client.base_url = None

    with pytest.raises(ValueError, match="Jarvis URL not configured"):
        asyncio.run(client.ocr_image(b"fake_image_bytes"))


def test_ocr_image_http_error():
    client = AIClient()
    client.base_url = "http://fake-url"

    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500 Server Error", request=MagicMock(), response=mock_resp
    )

    mock_post = AsyncMock(return_value=mock_resp)

    with patch("httpx.AsyncClient.post", mock_post):
        with pytest.raises(httpx.HTTPStatusError):
            asyncio.run(client.ocr_image(b"fake_image_bytes"))

    mock_post.assert_called_once()


def test_resolve_url_intent_exception_handling():
    ai_client.base_url = "http://test-jarvis.com"

    with patch("src.ai.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("Simulated connection error")
        mock_client_class.return_value.__aenter__.return_value = mock_client

        result = asyncio.run(ai_client.resolve_url_intent("http://example.com"))

    assert result == {"intent": "unknown", "confidence": 0.0}
    mock_client.post.assert_called_once()
    _, kwargs = mock_client.post.call_args
    assert kwargs["json"]["url"] == "http://example.com"
