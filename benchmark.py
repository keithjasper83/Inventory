import asyncio
import time
from fastapi import FastAPI, Depends, Request
from fastapi.testclient import TestClient
from src.main import app
from src.database import get_db
from src.dependencies import require_reviewer
import httpx

# Create a mock DB that sleeps to simulate a slow synchronous DB query
class SlowMockSession:
    def query(self, *args, **kwargs):
        return self
    def filter(self, *args, **kwargs):
        return self
    def first(self):
        time.sleep(0.1) # Simulate slow query (100ms)
        return None # We just want to hit the sleep
    def commit(self):
        pass

def override_get_db():
    yield SlowMockSession()

def override_require_reviewer():
    class User:
        id = 1
    return User()

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[require_reviewer] = override_require_reviewer

async def fetch(client):
    response = await client.post("/items/1/audit/1/undo")
    return response.status_code

async def run_benchmark():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Warmup
        await fetch(client)

        start = time.time()
        # Run 10 requests concurrently
        tasks = [fetch(client) for _ in range(10)]
        await asyncio.gather(*tasks)
        end = time.time()
        print(f"Time taken for 10 concurrent requests: {end - start:.4f} seconds")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
