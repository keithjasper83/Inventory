from src.models import Category, Location

def test_new_item_page(client, mock_db_session):
    # Setup mock returns
    mock_db_session.query.return_value.all.return_value = [
        Category(id=1, name="Test Cat", slug="test-cat"),
        Location(id=1, name="Test Loc", slug="test-loc")
    ]

    response = client.get("/new")
    assert response.status_code == 200
    assert "New Item" in response.text
    assert "Test Cat" in response.text

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_readiness_check(client):
    # In tests, deps may mock out or fail gracefully if test_db is not fully loaded with S3
    response = client.get("/readiness")
    assert response.status_code in [200, 503]
    assert "checks" in response.json()
