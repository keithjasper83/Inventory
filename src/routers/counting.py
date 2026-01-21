"""
Counting+ Feature: Bulk resistor counting and identification from photos.

This module provides endpoints for bulk resistor processing:
- Upload photo with multiple resistors
- AI identifies and counts each resistor
- Groups by value
- Flags unidentified components
- Batch add to inventory
"""

import os
import uuid
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Request, Form, UploadFile, File, HTTPException, status
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
import redis
from rq import Queue

from src.database import get_db
from src.models import Item, Media, Category, Location, Stock, AuditLog
from src.dependencies import templates, require_user, get_current_user
from src.storage import storage
from src.ai import ai_client
from src.config import settings
from src.tasks import create_audit_log, validate_ai_output

router = APIRouter()

# Redis Connection
try:
    if os.environ.get("TEST_MODE"):
        import fakeredis
        redis_conn = fakeredis.FakeRedis()
    else:
        redis_conn = redis.from_url(settings.REDIS_URL)
        redis_conn.ping()
except:
    import fakeredis
    print("Warning: Redis not available, using FakeRedis for Counting+")
    redis_conn = fakeredis.FakeRedis()

q = Queue(connection=redis_conn)


@router.get("/counting-plus", response_class=HTMLResponse)
async def counting_plus_page(request: Request, db: Session = Depends(get_db), user=Depends(require_user)):
    """Display the Counting+ upload page."""
    categories = db.query(Category).all()
    locations = db.query(Location).all()
    return templates.TemplateResponse(
        request=request,
        name="counting_plus.html",
        context={
            "request": request,
            "categories": categories,
            "locations": locations,
            "user": user
        }
    )


@router.post("/api/counting-plus/analyze")
async def analyze_resistors(
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    """
    Analyze a photo with multiple resistors and return identified components.
    
    This is the first step - analyze only, don't create items yet.
    Allows user to review results before adding to inventory.
    """
    if not photo.filename:
        raise HTTPException(status_code=400, detail="No photo provided")
    
    # Read image bytes
    image_bytes = await photo.read()
    
    # Call AI service
    try:
        result = await ai_client.count_resistors_bulk(image_bytes)
    except ValueError as e:
        # Jarvis not configured, return mock data for testing
        result = {
            "resistors": [
                {"value": "10k", "ohms": 10000, "tolerance": "5%", "confidence": 0.98, "position": {"x": 100, "y": 150}},
                {"value": "10k", "ohms": 10000, "tolerance": "5%", "confidence": 0.96, "position": {"x": 120, "y": 150}},
                {"value": "100", "ohms": 100, "tolerance": "5%", "confidence": 0.95, "position": {"x": 140, "y": 150}},
                {"value": "unknown", "ohms": None, "tolerance": None, "confidence": 0.2, "position": {"x": 160, "y": 150}},
            ],
            "total_count": 4,
            "failed_count": 1,
            "grouped": {
                "10k": 2,
                "100": 1,
                "unknown": 1
            },
            "warning": "Jarvis not configured - using mock data for testing"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI analysis failed: {str(e)}")
    
    # Store image temporarily for batch creation
    temp_key = f"temp/counting-plus/{uuid.uuid4()}-{photo.filename}"
    await photo.seek(0)  # Reset file pointer
    await run_in_threadpool(storage.upload_file, photo.file, temp_key, photo.content_type)
    
    # Return results with temp key for batch creation
    result["temp_image_key"] = temp_key
    result["analyzed_by"] = user.username if hasattr(user, 'username') else "unknown"
    
    return JSONResponse(content=result)


@router.post("/api/counting-plus/batch-create")
async def batch_create_resistors(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    """
    Batch create items from analyzed resistors.
    
    Expected payload:
    {
        "temp_image_key": "temp/counting-plus/...",
        "location_id": 1,
        "category_id": 2,
        "resistors": [
            {"value": "10k", "ohms": 10000, "tolerance": "5%", "confidence": 0.98, "add": true},
            ...
        ]
    }
    """
    data = await request.json()
    
    temp_image_key = data.get("temp_image_key")
    location_id = data.get("location_id")
    category_id = data.get("category_id")
    resistors = data.get("resistors", [])
    
    if not location_id:
        raise HTTPException(status_code=400, detail="Location ID required")
    
    # Validate location exists
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    
    # Group resistors by value for batch processing
    grouped_by_value: Dict[str, List[Dict[str, Any]]] = {}
    for resistor in resistors:
        if not resistor.get("add", True):  # Skip if user unmarked it
            continue
        value = resistor.get("value", "unknown")
        if value not in grouped_by_value:
            grouped_by_value[value] = []
        grouped_by_value[value].append(resistor)
    
    created_items = []
    failed_items = []
    
    # Create items grouped by value
    for value, resistor_list in grouped_by_value.items():
        if value == "unknown":
            # Create individual items for unknown resistors
            for resistor in resistor_list:
                try:
                    item = _create_resistor_item(
                        db, 
                        location_id, 
                        category_id, 
                        resistor, 
                        temp_image_key,
                        user.id if hasattr(user, 'id') else None
                    )
                    created_items.append({
                        "id": item.id,
                        "name": item.name,
                        "value": value,
                        "confidence": resistor.get("confidence", 0)
                    })
                except Exception as e:
                    failed_items.append({
                        "value": value,
                        "error": str(e)
                    })
        else:
            # Create single item with quantity = count
            try:
                item = _create_resistor_item(
                    db,
                    location_id,
                    category_id,
                    resistor_list[0],  # Use first as template
                    temp_image_key,
                    user.id if hasattr(user, 'id') else None,
                    quantity=len(resistor_list)
                )
                created_items.append({
                    "id": item.id,
                    "name": item.name,
                    "value": value,
                    "quantity": len(resistor_list),
                    "confidence": resistor_list[0].get("confidence", 0)
                })
            except Exception as e:
                failed_items.append({
                    "value": value,
                    "count": len(resistor_list),
                    "error": str(e)
                })
    
    db.commit()
    
    # Clean up temp image
    try:
        if temp_image_key:
            await run_in_threadpool(storage.delete_file, temp_image_key)
    except:
        pass  # Don't fail if cleanup fails
    
    return JSONResponse(content={
        "success": True,
        "created_count": len(created_items),
        "failed_count": len(failed_items),
        "created_items": created_items,
        "failed_items": failed_items
    })


def _create_resistor_item(
    db: Session,
    location_id: int,
    category_id: Optional[int],
    resistor: Dict[str, Any],
    temp_image_key: Optional[str],
    user_id: Optional[int],
    quantity: int = 1
) -> Item:
    """
    Create a single item from resistor data.
    
    Args:
        db: Database session
        location_id: Location to store item
        category_id: Category for item (optional)
        resistor: Resistor data from AI
        temp_image_key: Temporary image key to copy
        user_id: User creating the item
        quantity: Quantity of this resistor
    
    Returns:
        Created Item
    """
    value = resistor.get("value", "unknown")
    ohms = resistor.get("ohms")
    tolerance = resistor.get("tolerance")
    confidence = resistor.get("confidence", 0)
    
    # Generate name
    if value != "unknown" and ohms:
        # Format resistance value
        if ohms >= 1_000_000:
            formatted_value = f"{ohms / 1_000_000:.1f}MΩ"
        elif ohms >= 1_000:
            formatted_value = f"{ohms / 1_000:.1f}kΩ"
        else:
            formatted_value = f"{ohms}Ω"
        
        name = f"Resistor {formatted_value}"
        if tolerance:
            name += f" {tolerance}"
    else:
        name = f"Unknown Resistor (Confidence: {confidence*100:.0f}%)"
    
    # Generate slug
    base_slug = name.lower().replace(" ", "-").replace("ω", "ohm")
    slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"
    
    # Item data
    item_data = {
        "resistance_ohms": ohms,
        "tolerance": tolerance,
        "ai_confidence": confidence,
        "source": "counting_plus",
        "value_display": value
    }
    
    # Determine if this should be considered AI-scraped or needs review
    source = "AI_SCRAPED" if confidence >= 0.95 else "AI_GENERATED"
    is_draft = confidence < 0.8  # Draft if low confidence
    
    # Create item
    item = Item(
        name=name,
        slug=slug,
        category_id=category_id,
        is_draft=is_draft,
        data=item_data
    )
    db.add(item)
    db.flush()  # Get ID
    
    # Copy image from temp if available
    if temp_image_key:
        try:
            # Copy temp image to permanent location
            new_key = f"items/{item.id}/counting-plus-{uuid.uuid4()}.jpg"
            # Note: This would need storage.copy_file implementation
            # For now, we'll skip copying to avoid complexity
            # In production, implement: storage.copy_file(temp_image_key, new_key)
            pass
        except:
            pass
    
    # Create stock entry
    stock = Stock(
        item_id=item.id,
        location_id=location_id,
        quantity=quantity
    )
    db.add(stock)
    
    # Create audit log
    create_audit_log(
        db=db,
        entity_type="Item",
        entity_id=item.id,
        action="CREATE",
        changes={"name": name, "quantity": quantity, "method": "counting_plus"},
        source=source,
        confidence=confidence,
        user_id=user_id,
        after_state=item_data
    )
    
    return item


@router.get("/counting-plus/test", response_class=HTMLResponse)
async def counting_plus_test_page(request: Request, user=Depends(require_user)):
    """Test interface for Counting+ feature."""
    return templates.TemplateResponse(
        request=request,
        name="test_counting_plus.html",
        context={"request": request, "user": user}
    )


@router.post("/api/counting-plus/test-analyze")
async def test_analyze(
    photo: UploadFile = File(...),
    user=Depends(require_user)
):
    """
    Test endpoint for analyzing resistors without creating items.
    Returns detailed diagnostic information.
    """
    if not photo.filename:
        raise HTTPException(status_code=400, detail="No photo provided")
    
    image_bytes = await photo.read()
    
    # Test with AI if available, otherwise use mock
    try:
        result = await ai_client.count_resistors_bulk(image_bytes)
        result["test_mode"] = False
        result["jarvis_available"] = True
    except ValueError:
        # Jarvis not configured
        result = {
            "resistors": [
                {"value": "10k", "ohms": 10000, "tolerance": "5%", "confidence": 0.98, "position": {"x": 100, "y": 150}},
                {"value": "10k", "ohms": 10000, "tolerance": "5%", "confidence": 0.96, "position": {"x": 120, "y": 150}},
                {"value": "100", "ohms": 100, "tolerance": "5%", "confidence": 0.95, "position": {"x": 140, "y": 150}},
                {"value": "1M", "ohms": 1000000, "tolerance": "5%", "confidence": 0.92, "position": {"x": 160, "y": 150}},
                {"value": "unknown", "ohms": None, "tolerance": None, "confidence": 0.2, "position": {"x": 180, "y": 150}},
            ],
            "total_count": 5,
            "failed_count": 1,
            "grouped": {
                "10k": 2,
                "100": 1,
                "1M": 1,
                "unknown": 1
            },
            "test_mode": True,
            "jarvis_available": False,
            "message": "Using mock data - Jarvis not configured"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    
    # Add validation info
    result["validation"] = {
        "total_analyzed": len(result.get("resistors", [])),
        "high_confidence": len([r for r in result.get("resistors", []) if r.get("confidence", 0) >= 0.95]),
        "medium_confidence": len([r for r in result.get("resistors", []) if 0.8 <= r.get("confidence", 0) < 0.95]),
        "low_confidence": len([r for r in result.get("resistors", []) if r.get("confidence", 0) < 0.8]),
    }
    
    return JSONResponse(content=result)
