import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from src.tasks import process_item_image
from src.models import Item, Media

@patch("src.tasks.SessionLocal")
@patch("src.tasks.storage")
@patch("src.tasks.ai_client")
@patch("src.tasks.Image") # Mock PIL
def test_process_item_image(mock_image, mock_ai, mock_storage, mock_session_cls):
    # Setup Mock DB
    mock_db = MagicMock()
    mock_session_cls.return_value = mock_db

    item = Item(id=1, name=None, is_draft=True, data={}, pending_changes={})
    media = Media(id=1, s3_key="test/key", type="image")

    # Mock query results
    # First query is Item, second is Media
    mock_db.query.return_value.filter.return_value.first.side_effect = [item, media]

    # Mock Storage
    mock_storage.bucket_media = "test-bucket"
    mock_storage.s3_client.download_fileobj = MagicMock()

    # Mock PIL
    mock_img_instance = MagicMock()
    mock_img_instance.format = "JPEG"
    mock_image.open.return_value = mock_img_instance

    # Mock AI
    mock_ai.ocr_image = AsyncMock(return_value={"text": "Resistor 10k", "confidence": 0.99})
    mock_ai.identify_resistor = AsyncMock(return_value={"is_resistor": True, "resistance": 10000, "tolerance": 5, "confidence": 0.98})
    mock_ai.find_product_url = AsyncMock(return_value="http://example.com/resistor")
    mock_ai.scrape_url = AsyncMock(return_value={"datasheets": []})

    # Run
    process_item_image(1, 1)

    # Verify Item Updates (Name goes to item directly if draft)
    assert item.name == "Resistor 10k"
    assert item.slug == "resistor-10k"

    # Verify Pending Changes (Resistance/Tolerance go to pending)
    # The failing test expected data['resistance'], but we moved it to pending_changes
    assert item.pending_changes['resistance'] == 10000
    assert item.pending_changes['tolerance'] == 5

    # Verify Audit Log
    assert mock_db.add.call_count >= 2

    mock_db.commit.assert_called()

    # Verify Scraping Triggered (since confidence 0.99 >= 0.95)
    mock_ai.find_product_url.assert_called_with("Resistor 10k")
    mock_ai.scrape_url.assert_called_with("http://example.com/resistor")
