import asyncio
import time
import httpx
from fastapi import FastAPI

async def run_benchmark():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        # We need the server to be running
        # Let's send 50 requests concurrently and measure the time

        # Prepare form data
        files = {'photo': ('test.jpg', b'dummy content', 'image/jpeg')}
        data = {
            'name': 'Benchmark Item',
            'location_id': 1,
            'quantity': 10
        }

        start = time.time()
        tasks = []
        for _ in range(20):
            tasks.append(client.post("/items", data=data, files={'photo': ('test.jpg', b'dummy content', 'image/jpeg')}))

        responses = await asyncio.gather(*tasks)
        end = time.time()

        print(f"Total time for 20 requests: {end - start:.2f}s")
        print(f"Status codes: {[r.status_code for r in responses]}")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
