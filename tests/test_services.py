import pytest
from unittest.mock import MagicMock

from src.domain.services import ItemService

def test_approve_pending_changes_invalid_id():
    mock_db = MagicMock()
    service = ItemService(db=mock_db)

    # Mock item_repo to return None
    service.item_repo.get_by_id = MagicMock(return_value=None)

    with pytest.raises(ValueError) as excinfo:
        service.approve_pending_changes(999)

    assert str(excinfo.value) == "Item 999 not found"
