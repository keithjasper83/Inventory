from unittest.mock import MagicMock, patch

from src.domain.media_service import MediaService


@patch("src.domain.media_service.logger.error")
def test_generate_thumbnails_exception(mock_logger_error):
    media_service = MediaService(MagicMock())

    result = media_service.generate_thumbnails(
        b"not an image",
        item_id=1,
        original_filename="test.jpg",
    )

    assert result == {}
    mock_logger_error.assert_called_once()
    assert "Error generating thumbnails:" in mock_logger_error.call_args[0][0]
