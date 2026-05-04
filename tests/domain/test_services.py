import pytest
from unittest.mock import MagicMock, patch
from src.domain.services import ItemService
from src.models import Item

class TestItemService:
    def setup_method(self):
        self.db = MagicMock()
        self.service = ItemService(self.db)

    @patch('src.domain.services.create_audit_log')
    def test_approve_pending_changes(self, mock_create_audit_log):
        # Setup
        item_id = 1
        item = Item(
            id=item_id,
            name="Test Item",
            data={"existing_key": "existing_value"},
            pending_changes={"new_key": "new_value", "existing_key": "updated_value"}
        )
        self.service.item_repo.get_by_id = MagicMock(return_value=item)

        # Execute
        result = self.service.approve_pending_changes(item_id)

        # Assert
        self.service.item_repo.get_by_id.assert_called_once_with(item_id)
        assert result.data == {"existing_key": "updated_value", "new_key": "new_value"}
        assert not result.pending_changes

        mock_create_audit_log.assert_called_once_with(
            db=self.db,
            entity_type="Item",
            entity_id=item_id,
            action="APPROVE",
            changes={"new_key": "new_value", "existing_key": "updated_value"},
            source="USER"
        )
        self.db.commit.assert_called_once()

    def test_approve_pending_changes_item_not_found(self):
        # Setup
        item_id = 1
        self.service.item_repo.get_by_id = MagicMock(return_value=None)

        # Execute & Assert
        with pytest.raises(ValueError, match=f"Item {item_id} not found"):
            self.service.approve_pending_changes(item_id)

    @patch('src.domain.services.create_audit_log')
    def test_approve_pending_changes_no_pending(self, mock_create_audit_log):
        # Setup
        item_id = 1
        item = Item(
            id=item_id,
            name="Test Item",
            data={"existing_key": "existing_value"},
            pending_changes=None
        )
        self.service.item_repo.get_by_id = MagicMock(return_value=item)

        # Execute
        result = self.service.approve_pending_changes(item_id)

        # Assert
        assert result.data == {"existing_key": "existing_value"}
        mock_create_audit_log.assert_not_called()
        self.db.commit.assert_not_called()
