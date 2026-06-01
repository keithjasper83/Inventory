import pytest
import httpx
import asyncio
from unittest.mock import patch, MagicMock

from src.ai import AIClient
from src.config import settings

def test_check_health_network_error():
    """Test check_health handles network errors correctly and returns False."""
    client = AIClient()
    client.base_url = "http://fake-url"

    # Create a mock for httpx.AsyncClient
    with patch("httpx.AsyncClient") as MockAsyncClient:
        # Get the instance that the context manager will return
        mock_instance = MockAsyncClient.return_value.__aenter__.return_value

        # Make the get method raise a NetworkError
        mock_instance.get.side_effect = httpx.NetworkError("Network issue")

        # Call the check_health method within asyncio.run
        result = asyncio.run(client.check_health())

        # Assert that the method returns False
        assert result is False
