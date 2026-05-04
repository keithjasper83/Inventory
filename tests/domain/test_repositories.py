from unittest.mock import MagicMock
from src.domain.repositories import ItemRepository
from src.models import Item

def test_item_repository_create():
    """Test that ItemRepository.create calls db.add and db.flush with the correct item."""
    # Arrange
    mock_db = MagicMock()
    repo = ItemRepository(db=mock_db)
    mock_item = Item(name="Test Item")

    # Act
    result = repo.create(mock_item)

    # Assert
    mock_db.add.assert_called_once_with(mock_item)
    mock_db.flush.assert_called_once()
    assert result == mock_item
