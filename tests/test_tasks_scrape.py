import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from src.tasks import scrape_item_task
from src.models import Item

@patch("src.tasks.SessionLocal")
@patch("src.tasks.storage")
@patch("src.tasks.ai_client")
def test_scrape_item_task(mock_ai, mock_storage, mock_session_cls):
    # Setup Mock DB
    mock_db = MagicMock()
    mock_session_cls.return_value = mock_db

    item = Item(id=1, name="Resistor 10k", is_draft=True, data={}, pending_changes={"ocr_text": "Resistor 10k"})

    # Mock query results
    mock_db.query.return_value.filter.return_value.first.return_value = item

    # Mock AI
    mock_ai.find_product_url = AsyncMock(return_value="http://example.com/resistor")
    mock_ai.scrape_url = AsyncMock(return_value={"datasheets": ["http://example.com/datasheet.pdf"]})

    # Run
    scrape_item_task(1)

    # Verify Pending Changes
    assert item.pending_changes['source_url'] == "http://example.com/resistor"

    # Verify Audit Log
    assert mock_db.add.call_count >= 1

    mock_db.commit.assert_called()

    # Verify Scraping Triggered
    mock_ai.find_product_url.assert_called_with("Resistor 10k")
    mock_ai.scrape_url.assert_called_with("http://example.com/resistor")
