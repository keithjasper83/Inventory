from src.models import User
from src.auth import auth_service

def test_login_success(client, mock_db_session):
    mock_user = User(id=1, username="testuser", password_hash=auth_service.get_password_hash("password123"))
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user

    response = client.post("/login", data={"username": "testuser", "password": "password123"}, follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/"
    assert response.cookies.get("session")  # Session cookie should be set

def test_login_invalid_password(client, mock_db_session):
    mock_user = User(id=1, username="testuser", password_hash=auth_service.get_password_hash("password123"))
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user

    response = client.post("/login", data={"username": "testuser", "password": "wrongpassword"}, follow_redirects=False)

    assert response.status_code == 200 # returns HTML
    assert "Invalid credentials" in response.text

def test_login_invalid_user(client, mock_db_session):
    mock_db_session.query.return_value.filter.return_value.first.return_value = None

    response = client.post("/login", data={"username": "wronguser", "password": "password123"}, follow_redirects=False)

    assert response.status_code == 200 # returns HTML
    assert "Invalid credentials" in response.text


def test_logout(client):
    response = client.get("/logout", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"

def test_login_page(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert "Login" in response.text
