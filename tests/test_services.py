from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from src.domain.services import ItemCreateDTO, ItemService
from src.models import Stock
from src.tasks import AuditLogParams


@patch("src.domain.services.create_audit_log")
def test_create_item_with_name(mock_create_audit_log):
    mock_db = MagicMock(spec=Session)
    service = ItemService(mock_db)
    service.item_repo = MagicMock()
    service.stock_repo = MagicMock()

    def create_item(item):
        item.id = 1
        return item

    service.item_repo.create.side_effect = create_item

    item = service.create_item(
        ItemCreateDTO(
            name="Resistor",
            location_id=1,
            category_id=2,
            quantity=100,
            data={"resistance": "10k"},
        )
    )

    assert item.name == "Resistor"
    assert item.slug.startswith("resistor-")
    assert item.category_id == 2
    assert item.is_draft is False
    assert item.data == {"resistance": "10k"}

    service.item_repo.create.assert_called_once()
    service.stock_repo.create.assert_called_once()
    created_stock = service.stock_repo.create.call_args[0][0]
    assert isinstance(created_stock, Stock)
    assert created_stock.item_id == item.id
    assert created_stock.location_id == 1
    assert created_stock.quantity == 100

    audit_params = mock_create_audit_log.call_args.args[0]
    assert isinstance(audit_params, AuditLogParams)
    assert audit_params.db == mock_db
    assert audit_params.entity_type == "Item"
    assert audit_params.entity_id == item.id
    assert audit_params.action == "CREATE"
    assert audit_params.changes == {"name": "Resistor", "is_draft": False}
    assert audit_params.source == "USER"
    mock_db.commit.assert_called_once()


@patch("src.domain.services.create_audit_log")
def test_create_item_draft(mock_create_audit_log):
    mock_db = MagicMock(spec=Session)
    service = ItemService(mock_db)
    service.item_repo = MagicMock()
    service.stock_repo = MagicMock()

    def create_item(item):
        item.id = 1
        return item

    service.item_repo.create.side_effect = create_item

    item = service.create_item(
        ItemCreateDTO(
            name=None,
            location_id=1,
            category_id=None,
            quantity=10,
            data={},
        )
    )

    assert item.name is None
    assert item.slug is None
    assert item.category_id is None
    assert item.is_draft is True
    assert item.data == {}

    service.item_repo.create.assert_called_once()
    service.stock_repo.create.assert_called_once()
    created_stock = service.stock_repo.create.call_args[0][0]
    assert isinstance(created_stock, Stock)
    assert created_stock.item_id == item.id
    assert created_stock.location_id == 1
    assert created_stock.quantity == 10

    audit_params = mock_create_audit_log.call_args.args[0]
    assert isinstance(audit_params, AuditLogParams)
    assert audit_params.changes == {"name": None, "is_draft": True}
    assert audit_params.source == "USER"
    mock_db.commit.assert_called_once()


def test_approve_pending_changes_invalid_id():
    service = ItemService(db=MagicMock())
    service.item_repo.get_by_id = MagicMock(return_value=None)

    with pytest.raises(ValueError, match="Item 999 not found"):
        service.approve_pending_changes(999)
