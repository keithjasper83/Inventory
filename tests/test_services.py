import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from src.domain.services import ItemService
from src.models import Item, Stock

@patch("src.domain.services.AuditLogRepository")
@patch("src.domain.services.MediaRepository")
@patch("src.domain.services.StockRepository")
@patch("src.domain.services.ItemRepository")
@patch("src.domain.services.create_audit_log")
def test_create_item_with_name(mock_create_audit_log, mock_item_repo, mock_stock_repo, mock_media_repo, mock_audit_repo):
    # Mocking
    mock_db = MagicMock(spec=Session)

    mock_item_repo_instance = MagicMock()
    mock_item_repo.return_value = mock_item_repo_instance
    mock_item_repo_instance.create.side_effect = lambda item: item

    mock_stock_repo_instance = MagicMock()
    mock_stock_repo.return_value = mock_stock_repo_instance

    # Initialize service
    service = ItemService(mock_db)

    # Call create_item
    item = service.create_item(
        name="Resistor",
        location_id=1,
        category_id=2,
        quantity=100,
        data={"resistance": "10k"}
    )

    # Assertions
    assert item.name == "Resistor"
    assert item.slug.startswith("resistor-")
    assert item.category_id == 2
    assert item.is_draft is False
    assert item.data == {"resistance": "10k"}

    mock_item_repo_instance.create.assert_called_once()

    mock_stock_repo_instance.create.assert_called_once()
    created_stock = mock_stock_repo_instance.create.call_args[0][0]
    assert isinstance(created_stock, Stock)
    assert created_stock.item_id == item.id
    assert created_stock.location_id == 1
    assert created_stock.quantity == 100

    mock_create_audit_log.assert_called_once_with(
        db=mock_db,
        entity_type="Item",
        entity_id=item.id,
        action="CREATE",
        changes={"name": "Resistor", "is_draft": False},
        source="USER"
    )

    mock_db.commit.assert_called_once()

@patch("src.domain.services.AuditLogRepository")
@patch("src.domain.services.MediaRepository")
@patch("src.domain.services.StockRepository")
@patch("src.domain.services.ItemRepository")
@patch("src.domain.services.create_audit_log")
def test_create_item_draft(mock_create_audit_log, mock_item_repo, mock_stock_repo, mock_media_repo, mock_audit_repo):
    # Mocking
    mock_db = MagicMock(spec=Session)

    mock_item_repo_instance = MagicMock()
    mock_item_repo.return_value = mock_item_repo_instance
    mock_item_repo_instance.create.side_effect = lambda item: item

    mock_stock_repo_instance = MagicMock()
    mock_stock_repo.return_value = mock_stock_repo_instance

    # Initialize service
    service = ItemService(mock_db)

    # Call create_item
    item = service.create_item(
        name=None,
        location_id=1,
        category_id=None,
        quantity=10,
        data={}
    )

    # Assertions
    assert item.name is None
    assert item.slug is None
    assert item.category_id is None
    assert item.is_draft is True
    assert item.data == {}

    mock_item_repo_instance.create.assert_called_once()

    mock_stock_repo_instance.create.assert_called_once()
    created_stock = mock_stock_repo_instance.create.call_args[0][0]
    assert isinstance(created_stock, Stock)
    assert created_stock.item_id == item.id
    assert created_stock.location_id == 1
    assert created_stock.quantity == 10

    mock_create_audit_log.assert_called_once_with(
        db=mock_db,
        entity_type="Item",
        entity_id=item.id,
        action="CREATE",
        changes={"name": None, "is_draft": True},
        source="USER"
    )

    mock_db.commit.assert_called_once()
