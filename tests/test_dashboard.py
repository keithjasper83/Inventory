def test_dashboard_total_items(client, mock_db_session):
    # Setup mock return value for scalar count query
    mock_db_session.scalar.return_value = 42

    response = client.get("/")
    assert response.status_code == 200
    assert "Total Items" in response.text
    assert "42" in response.text
    mock_db_session.scalar.assert_called_once()
