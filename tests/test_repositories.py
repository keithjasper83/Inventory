from unittest.mock import MagicMock

from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import BinaryExpression

from src.domain.repositories import ItemRepository
from src.models import Item


def test_item_repository_get_by_id(mock_db_session):
    mock_query = mock_db_session.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_item = Item(id=1, name="Test Item")
    mock_filter.first.return_value = mock_item

    repo = ItemRepository(db=mock_db_session)
    result = repo.get_by_id(1)

    mock_db_session.query.assert_called_once_with(Item)
    mock_filter.first.assert_called_once()
    assert result == mock_item


def test_item_repository_get_by_id_not_found(mock_db_session):
    mock_query = mock_db_session.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_filter.first.return_value = None

    repo = ItemRepository(db=mock_db_session)
    result = repo.get_by_id(999)

    mock_db_session.query.assert_called_once_with(Item)
    mock_filter.first.assert_called_once()
    assert result is None


def test_search_by_text_fallback():
    db_mock = MagicMock(spec=Session)
    repo = ItemRepository(db=db_mock)
    query = "test_query"
    expected_result = [Item(id=1, name="test fallback")]

    query_mock = MagicMock()
    db_mock.query.return_value = query_mock

    filter_mock_1 = MagicMock()
    filter_mock_2 = MagicMock()
    query_mock.filter.side_effect = [filter_mock_1, filter_mock_2]

    filter_mock_1.params.side_effect = Exception("DB error")
    filter_mock_2.all.return_value = expected_result

    result = repo.search_by_text(query)

    assert result == expected_result
    assert query_mock.filter.call_count == 2

    args, _ = query_mock.filter.call_args_list[1]
    clause = args[0]
    assert isinstance(clause, BinaryExpression)
    assert clause.right.value == f"%{query}%"
