import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import httpx
from src.ai import AIClient

def test_ocr_image_success():
    """Test successful OCR image processing."""
    client = AIClient()
    client.base_url = "http://fake-url"

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"text": "Hello World"}
    # raise_for_status should do nothing on 200
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
    """Test OCR image processing with missing URL."""
    client = AIClient()
    client.base_url = None

    with pytest.raises(ValueError, match="Jarvis URL not configured"):
        asyncio.run(client.ocr_image(b"fake_image_bytes"))

def test_ocr_image_http_error():
    """Test OCR image processing when an HTTP error occurs."""
    client = AIClient()
    client.base_url = "http://fake-url"

    mock_resp = MagicMock()
    mock_resp.status_code = 500
    # Make raise_for_status raise an HTTPStatusError
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500 Server Error", request=MagicMock(), response=mock_resp
    )

    mock_post = AsyncMock(return_value=mock_resp)

    with patch("httpx.AsyncClient.post", mock_post):
        with pytest.raises(httpx.HTTPStatusError):
            asyncio.run(client.ocr_image(b"fake_image_bytes"))

        mock_post.assert_called_once()
