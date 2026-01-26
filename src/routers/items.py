import os
from typing import List, Optional
from fastapi import APIRouter, Depends, Request, Form, UploadFile, File, HTTPException, status
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from sqlalchemy import or_
import uuid
import logging

import redis
from rq import Queue
from src.database import get_db
from src.models import Item, Media, Category, Location, Stock, AuditLog
from src.dependencies import templates, require_user, get_current_user
from src.storage import storage
from src.ai import ai_client
from src.tasks import process_item_image
from src.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Redis Connection
try:
    if os.environ.get("TEST_MODE"):
        import fakeredis
        redis_conn = fakeredis.FakeRedis()
    else:
        redis_conn = redis.from_url(settings.REDIS_URL)
        redis_conn.ping() # Check connection
except:
    import fakeredis
    logger.warning("Redis not available, using FakeRedis")
    redis_conn = fakeredis.FakeRedis()

q = Queue(connection=redis_conn)

@router.get("/new", response_class=HTMLResponse)
async def new_item_page(request: Request, db: Session = Depends(get_db), user=Depends(require_user)):
    categories = db.query(Category).all()
    locations = db.query(Location).all()
    return templates.TemplateResponse(
        request=request,
        name="item_new.html",
        context={"request": request, "categories": categories, "locations": locations}
    )

@router.post("/items")
async def create_item(
    request: Request,
    name: Optional[str] = Form(None),
    location_id: int = Form(...),
    category_id: Optional[int] = Form(None),
    quantity: int = Form(1),
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    # Create Item (Draft if name missing, though name or photo is required, photo is enforced by type)
    is_draft = name is None

    # Generate slug if name provided
    slug = None
    if name:
        base_slug = name.lower().replace(" ", "-") # Simple slugify
        slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"

    # Extract Dynamic Data (prefixed with data_)
    form_data = await request.form()
    item_data = {}
    for key, value in form_data.items():
        if key.startswith("data_"):
            clean_key = key.replace("data_", "")
            item_data[clean_key] = value

    item = Item(
        name=name,
        slug=slug,
        category_id=category_id,
        is_draft=is_draft,
        data=item_data
    )
    db.add(item)
    db.flush() # Get ID

    # Handle Photo
    if photo.filename:
        key = f"items/{item.id}/{uuid.uuid4()}-{photo.filename}"

        # Non-blocking upload
        await run_in_threadpool(storage.upload_file, photo.file, key, photo.content_type)

        media = Media(
            item_id=item.id,
            type="image",
            s3_key=key
        )
        db.add(media)

    # Handle Stock
    stock = Stock(item_id=item.id, location_id=location_id, quantity=quantity)
    db.add(stock)

    # Audit Log
    audit = AuditLog(
        entity_type="Item",
        entity_id=item.id,
        action="CREATE",
        changes={"name": name, "is_draft": is_draft},
        source="USER"
    )
    db.add(audit)

    db.commit()

    # Trigger AI Jobs (Queued)
    if 'media' in locals() and media.id:
        q.enqueue(process_item_image, item.id, media.id)

    if item.slug:
        return RedirectResponse(url=f"/i/{item.slug}", status_code=status.HTTP_303_SEE_OTHER)
    else:
        return RedirectResponse(url=f"/p/{item.id}", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/i/{slug}", response_class=HTMLResponse)
async def view_item_slug(slug: str, request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    item = db.query(Item).filter(Item.slug == slug).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Audit Logs
    audit_logs = db.query(AuditLog).filter(AuditLog.entity_id == item.id).order_by(AuditLog.timestamp.desc()).all()

    # Generate Presigned URLs for media
    media_list = []
    for m in item.media:
        url = storage.get_presigned_url(m.s3_key)
        media_list.append({
            "type": m.type,
            "s3_key": m.s3_key,
            "url": url,
            "metadata": m.metadata_json
        })

    return templates.TemplateResponse(
        request=request,
        name="item_detail.html",
        context={"request": request, "item": item, "user": user, "media_list": media_list, "audit_logs": audit_logs}
    )

@router.get("/p/{id}", response_class=HTMLResponse)
async def view_item_id(id: int, request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    item = db.query(Item).filter(Item.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if item.slug:
        return RedirectResponse(url=f"/i/{item.slug}", status_code=status.HTTP_301_MOVED_PERMANENTLY)

    # Audit Logs
    audit_logs = db.query(AuditLog).filter(AuditLog.entity_id == item.id).order_by(AuditLog.timestamp.desc()).all()

    media_list = []
    for m in item.media:
        url = storage.get_presigned_url(m.s3_key)
        media_list.append({
            "type": m.type,
            "s3_key": m.s3_key,
            "url": url,
            "metadata": m.metadata_json
        })

    return templates.TemplateResponse(
        request=request,
        name="item_detail.html",
        context={"request": request, "item": item, "user": user, "media_list": media_list, "audit_logs": audit_logs}
    )

@router.post("/items/{id}/approve")
async def approve_changes(id: int, request: Request, db: Session = Depends(get_db), user=Depends(require_user)):
    item = db.query(Item).filter(Item.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if item.pending_changes:
        # Shallow merge data (top level keys)
        data = dict(item.data)
        data.update(item.pending_changes)
        item.data = data
        item.pending_changes = {}

        audit = AuditLog(
            entity_type="Item",
            entity_id=item.id,
            action="APPROVE",
            changes=item.pending_changes,
            source="USER"
        )
        db.add(audit)
        db.commit()

    return RedirectResponse(url=f"/p/{id}", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/items/{id}/reject")
async def reject_changes(id: int, request: Request, db: Session = Depends(get_db), user=Depends(require_user)):
    item = db.query(Item).filter(Item.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if item.pending_changes:
        item.pending_changes = {}

        audit = AuditLog(
            entity_type="Item",
            entity_id=item.id,
            action="REJECT",
            changes={},
            source="USER"
        )
        db.add(audit)
        db.commit()

    return RedirectResponse(url=f"/p/{id}", status_code=status.HTTP_303_SEE_OTHER)
@router.post("/items/{id}/audit/{log_id}/undo")
async def undo_change(id: int, log_id: int, request: Request, db: Session = Depends(get_db), user=Depends(require_user)):
    item = db.query(Item).filter(Item.id == id).first()
    log = db.query(AuditLog).filter(AuditLog.id == log_id, AuditLog.entity_id == id).first()

    if not item or not log:
        raise HTTPException(status_code=404, detail="Item or Log not found")

    if log.is_undone:
        raise HTTPException(status_code=400, detail="Change already undone")

    if not log.previous_values:
        raise HTTPException(status_code=400, detail="Cannot undo: No previous values recorded")

    # Apply previous values
    # We need to be careful about what 'previous_values' contains.
    # Assuming it's a dict of {field: old_value} matching Item columns or Item.data keys.

    current_data = dict(item.data)
    changes_made = {}

    for key, value in log.previous_values.items():
        # Check if key is a column or data key
        if hasattr(item, key) and key not in ['data', 'id', 'created_at']:
            setattr(item, key, value)
            changes_made[key] = value
        else:
            # Assume it's in data
            current_data[key] = value
            changes_made[key] = value

    item.data = current_data

    # Mark log as undone
    log.is_undone = True

    # Create new audit log for the undo
    undo_log = AuditLog(
        entity_type="Item",
        entity_id=item.id,
        action="UNDO",
        changes=changes_made, # What we reverted TO
        source="USER",
        confidence=100
    )
    db.add(undo_log)
    db.commit()

    return RedirectResponse(url=f"/p/{id}", status_code=status.HTTP_303_SEE_OTHER)
