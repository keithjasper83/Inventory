import pytest
from src.domain.repositories import ItemRepository
from src.models import Item

def test_item_repository_get_by_id(mock_db_session):
    # Setup
    mock_query = mock_db_session.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_item = Item(id=1, name="Test Item")
    mock_filter.first.return_value = mock_item

    repo = ItemRepository(db=mock_db_session)

    # Execute
    result = repo.get_by_id(1)

    # Verify
    mock_db_session.query.assert_called_once_with(Item)
    mock_filter.first.assert_called_once()
    assert result == mock_item

def test_item_repository_get_by_id_not_found(mock_db_session):
    # Setup
    mock_query = mock_db_session.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_filter.first.return_value = None

    repo = ItemRepository(db=mock_db_session)

    # Execute
    result = repo.get_by_id(999)

    # Verify
    mock_db_session.query.assert_called_once_with(Item)
    mock_filter.first.assert_called_once()
    assert result is None
