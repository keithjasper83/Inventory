import asyncio
import time
from src.main import app
from httpx import AsyncClient, ASGITransport

async def run_benchmark():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Warmup
        try:
            await client.get("/new")
        except Exception:
            pass

        start_time = time.time()
        # Simulate 1000 concurrent requests
        tasks = [client.get("/new") for _ in range(1000)]
        await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        print(f"1000 concurrent requests took: {end_time - start_time:.4f}s")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
