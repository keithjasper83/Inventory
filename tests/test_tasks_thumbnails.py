import pytest
from unittest.mock import patch
from src.tasks import generate_thumbnails

@patch("src.tasks.logger.error")
def test_generate_thumbnails_exception(mock_logger_error):
    # Passing malformed bytes will cause PIL.Image.open to raise an exception
    malformed_bytes = b"not an image"

    result = generate_thumbnails(malformed_bytes, item_id=1, original_filename="test.jpg")

    assert result == {}
    mock_logger_error.assert_called_once()
    assert "Error generating thumbnails:" in mock_logger_error.call_args[0][0]
