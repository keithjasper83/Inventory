from unittest.mock import MagicMock
from src.models import Item

def test_dashboard_total_items(client, mock_db_session):
    # Setup mock return value for Item count
    mock_db_session.query.return_value.count.return_value = 42

    response = client.get("/")
    assert response.status_code == 200
    assert "Total Items" in response.text
    assert "42" in response.text
