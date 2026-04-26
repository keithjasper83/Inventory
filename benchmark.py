import time
import asyncio
from fastapi import FastAPI
from sqlalchemy import create_engine, Column, Integer, JSON
from sqlalchemy.orm import sessionmaker, declarative_base
from fastapi.testclient import TestClient

# setup minimal app
app = FastAPI()
Base = declarative_base()

class Category(Base):
    __tablename__ = 'categories'
    id = Column(Integer, primary_key=True)
    schema = Column(JSON)

engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

db = SessionLocal()
db.add(Category(id=1, schema={"test": "data"}))
db.commit()

# Simulate a slow DB query inside an async endpoint (blocks the event loop)
@app.get("/async_schema")
async def get_category_schema_async():
    time.sleep(0.05) # Simulated slow DB call
    return {"schema": {"test": "data"}}

# Simulate a slow DB query inside a sync endpoint (FastAPI runs this in a thread pool)
@app.get("/sync_schema")
def get_category_schema_sync():
    time.sleep(0.05) # Simulated slow DB call
    return {"schema": {"test": "data"}}

@app.get("/health")
async def health():
    # Fast endpoint to measure event loop responsiveness
    return {"status": "ok"}
