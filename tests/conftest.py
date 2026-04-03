import os
os.environ['TEST_MODE'] = '1'

import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from src.main import app
from src.database import get_db
from src.dependencies import get_current_user

@pytest.fixture
def mock_db_session():
    session = MagicMock()
    return session

@pytest.fixture
def client(mock_db_session):
    def override_get_db():
        try:
            yield mock_db_session
        finally:
            pass

    # Mock user
    def override_get_current_user():
        user = MagicMock()
        user.id = 1
        user.username = "testuser"
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
