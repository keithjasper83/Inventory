import asyncio
import time
from src.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

def benchmark():
    # Warm up
    try:
        client.get("/new")
    except Exception as e:
        print("Warm up error (expected if test db not fully setup, but we just want to hit the route):", e)

    start_time = time.time()
    for _ in range(50):
        try:
            client.get("/new")
        except Exception:
            pass
    end_time = time.time()
    print(f"50 synchronous requests took: {end_time - start_time:.4f}s")

if __name__ == "__main__":
    benchmark()
