import time
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from src.main import app
from src.database import get_db
from src.dependencies import require_user, get_current_user
import os

os.environ['TEST_MODE'] = '1'

def override_get_db():
    session = MagicMock()
    # Mock db.add, db.flush, db.commit
    item = MagicMock()
    item.id = 1
    item.slug = None

    media = MagicMock()
    media.id = 1

    session.add = MagicMock()
    session.flush = MagicMock()
    session.commit = MagicMock()
    yield session

def override_require_user():
    user = MagicMock()
    user.id = 1
    return user

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[require_user] = override_require_user
app.dependency_overrides[get_current_user] = override_require_user

client = TestClient(app)

def run_bench():
    start = time.time()
    for _ in range(100):
        data = {
            'name': 'Bench item',
            'location_id': '1',
            'quantity': '1',
        }
        files = {
            'photo': ('test.jpg', b'dummy', 'image/jpeg')
        }
        response = client.post("/items", data=data, files=files, follow_redirects=False)
        assert response.status_code in [302, 303], f"Unexpected status code {response.status_code}"
    end = time.time()
    return end - start

if __name__ == "__main__":
    import src.storage
    src.storage.storage.upload_file = MagicMock() # Mock the upload

    import src.routers.items
    src.routers.items.q.enqueue = MagicMock() # Mock the queue

    time_taken = run_bench()
    print(f"Time for 100 requests: {time_taken:.4f}s")
