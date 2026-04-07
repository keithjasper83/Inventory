import uuid
import json
import os
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, Request, Depends, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
import redis
from rq import Queue

from src.database import get_db
from src.models import Item, Media, AuditLog, Stock
from src.storage import storage
from src.tasks import process_item_image, create_audit_log
from src.config import settings
from src.dependencies import templates

logger = logging.getLogger(__name__)

router = APIRouter()

# Redis Connection (Reuse logic from items.py or similar, better to have a global dependency but doing inline for now to match style)
if settings.TEST_MODE:
    import fakeredis
    redis_conn = fakeredis.FakeRedis()
else:
    redis_conn = redis.from_url(settings.REDIS_URL)

q = Queue(connection=redis_conn)

SESSION_TTL = 600  # 10 minutes

@router.post("/api/companion/start")
async def start_companion_session():
    """Starts a new companion session and returns the ID."""
    session_id = str(uuid.uuid4())
    key = f"companion:{session_id}"

    data = {
        "status": "waiting",
        "created_at": str(uuid.uuid1())
    }

    redis_conn.setex(key, SESSION_TTL, json.dumps(data))

    return {"session_id": session_id}

@router.get("/companion/{session_id}", response_class=HTMLResponse)
async def companion_page(request: Request, session_id: str):
    """Serves the mobile upload page."""
    key = f"companion:{session_id}"
    if not redis_conn.exists(key):
        return HTMLResponse("<h1>Session Expired</h1><p>Please start a new session on your desktop.</p>", status_code=404)

    return templates.TemplateResponse(
        request=request,
        name="companion_upload.html",
        context={"request": request, "session_id": session_id}
    )

@router.post("/companion/{session_id}/upload")
async def companion_upload(
    session_id: str,
    photo: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Handles the file upload from mobile."""
    key = f"companion:{session_id}"
    if not redis_conn.exists(key):
        raise HTTPException(status_code=404, detail="Session expired")

    # Create Draft Item
    item = Item(
        name=None, # Draft
        is_draft=True,
        category_id=None
    )
    db.add(item)
    db.flush() # Get ID

    # Default Stock (required by schema usually, or good practice)
    # Using first location or default if possible.
    # For now, let's leave location null if schema allows, or pick the first one.
    # Looking at models.py, Stock requires location_id (PK).
    # We'll pick the first location ID available or 1.
    # Ideally, the user sets this later. But we need to insert *something* if we insert Stock.
    # However, create_item in items.py inserts Stock. Let's do the same here to be consistent.
    # If no locations exist, this might fail, but seed data usually exists.
    from src.models import Location
    default_loc = db.query(Location).first()
    loc_id = default_loc.id if default_loc else 1 # Fallback, might error if foreign key fails

    stock = Stock(item_id=item.id, location_id=loc_id, quantity=1)
    db.add(stock)

    # Handle Photo
    s3_key = f"items/{item.id}/{uuid.uuid4()}-{photo.filename}"
    await run_in_threadpool(storage.upload_file, photo.file, s3_key, photo.content_type)

    media = Media(
        item_id=item.id,
        type="image",
        s3_key=s3_key
    )
    db.add(media)

    # Audit
    create_audit_log(
        db=db,
        entity_type="Item",
        entity_id=item.id,
        action="CREATE",
        changes={"source": "companion_app"},
        source="USER"
    )
    db.commit()

    # Trigger AI
    try:
        q.enqueue(
            process_item_image,
            item.id,
            media.id,
            job_timeout=600,
            result_ttl=86400,
            failure_ttl=604800,
            retry=None
        )
    except Exception:
        logger.exception(f"Failed to enqueue process_item_image job for item {item.id} in companion mode")

    # Update Session Status
    new_data = {
        "status": "completed",
        "item_id": item.id,
        "slug": item.slug, # Likely None
        "redirect_url": f"/p/{item.id}"
    }
    redis_conn.setex(key, SESSION_TTL, json.dumps(new_data))

    return {"status": "ok", "item_id": item.id}

@router.get("/api/companion/{session_id}/status")
async def check_session_status(session_id: str):
    """Checks the status of the session."""
    key = f"companion:{session_id}"
    data = redis_conn.get(key)

    if not data:
        return {"status": "expired"}

    return json.loads(data)
