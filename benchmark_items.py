import asyncio
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database import Base
from src.models import Item, Category, AuditLog
from fastapi.concurrency import run_in_threadpool

# Mock DB session for testing query latency impact on event loop
class MockQuery:
    def options(self, *args):
        return self
    def filter(self, *args):
        return self
    def order_by(self, *args):
        return self
    def first(self):
        time.sleep(0.05) # simulate DB latency
        return "Item"
    def all(self):
        time.sleep(0.05) # simulate DB latency
        return ["Log1", "Log2"]

class MockSession:
    def query(self, *args):
        return MockQuery()

def sync_queries(db):
    item = db.query(Item).filter(Item.slug == "test").first()
    audit_logs = db.query(AuditLog).filter(AuditLog.entity_id == 1).order_by(AuditLog.timestamp.desc()).all()
    return item, audit_logs

async def async_queries(db):
    item = await run_in_threadpool(lambda: db.query(Item).filter(Item.slug == "test").first())
    audit_logs = await run_in_threadpool(lambda: db.query(AuditLog).filter(AuditLog.entity_id == 1).order_by(AuditLog.timestamp.desc()).all())
    return item, audit_logs

async def run_benchmark():
    db = MockSession()

    # Baseline
    start = time.time()
    # We run 10 concurrent requests
    # Since sync blocks the loop, they will run sequentially.
    async def run_sync_request():
        # Using a mock sleep to represent asyncio event loop doing other things is tricky since sync_queries blocks the thread.
        # If we have concurrent tasks that use CPU/blocking calls, asyncio gathers them sequentially.
        sync_queries(db)
        await asyncio.sleep(0) # yield

    await asyncio.gather(*(run_sync_request() for _ in range(10)))
    sync_time = time.time() - start

    # Optimized
    start = time.time()
    async def run_async_request():
        await async_queries(db)

    await asyncio.gather(*(run_async_request() for _ in range(10)))
    async_time = time.time() - start

    print(f"Sync time (Baseline): {sync_time:.2f}s")
    print(f"Async time (Optimized): {async_time:.2f}s")
    print(f"Improvement: {(sync_time - async_time) / sync_time * 100:.2f}%")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
