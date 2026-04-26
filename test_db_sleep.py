from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from src.database import get_db
import time

router = APIRouter()

@router.get("/test-sync")
async def test_sync(db: Session = Depends(get_db)):
    time.sleep(0.1) # Simulate slow query
    return {"status": "ok"}

@router.get("/test-async")
def test_async(db: Session = Depends(get_db)):
    time.sleep(0.1) # Simulate slow query
    return {"status": "ok"}
