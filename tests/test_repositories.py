import pytest
from unittest.mock import MagicMock
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import BinaryExpression

from src.domain.repositories import ItemRepository
from src.models import Item

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

    # First FTS query throws exception
    filter_mock_1.params.side_effect = Exception("DB error")

    # Second fallback query succeeds
    filter_mock_2.all.return_value = expected_result

    result = repo.search_by_text(query)

    assert result == expected_result
    assert query_mock.filter.call_count == 2

    # Check the argument to the second filter call (the fallback)
    args, kwargs = query_mock.filter.call_args_list[1]
    clause = args[0]

    assert isinstance(clause, BinaryExpression)
    assert clause.right.value == f"%{query}%"
