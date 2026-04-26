import time
import asyncio
from src.routers.admin import admin_dashboard
from fastapi import Request
from unittest.mock import MagicMock
import os
import sys
os.environ["TEST_MODE"] = "1"

# Mock the templates to avoid rendering errors and file IO
import src.dependencies
src.dependencies.templates.TemplateResponse = MagicMock(return_value="mock_response")

# We want to measure the blocking part (settings_manager.get_all) which we can simulate with sleep
import src.settings_manager
def mock_get_all():
    time.sleep(0.01) # Simulate slow DB call blocking the event loop
    return {}
src.settings_manager.settings_manager.get_all = mock_get_all

async def run_benchmark():
    request = MagicMock(spec=Request)
    db = MagicMock()
    user = MagicMock()

    start_time = time.time()
    # We run it concurrently to show event loop blocking issue
    tasks = [admin_dashboard(request, db, user) for _ in range(100)]
    await asyncio.gather(*tasks)
    end_time = time.time()

    print(f"Concurrent execution time for 100 calls: {end_time - start_time:.4f} seconds")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
