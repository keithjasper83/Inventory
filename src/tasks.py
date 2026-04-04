import time
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from src.database import SessionLocal
from src.models import Item, Media, AuditLog
from src.ai import ai_client
from src.config import settings
from src.storage import storage
from src.settings_manager import settings_manager
import asyncio
import io
from PIL import Image
from rq import get_current_job
from functools import wraps
import logging

logger = logging.getLogger(__name__)

# Constants for retry and AI validation
MAX_RETRIES = 3

def retry_with_backoff(max_retries=3, initial_backoff=1.0, backoff_multiplier=2.0):
    """
    Decorator for retrying functions with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts (total attempts)
        initial_backoff: Initial backoff time in seconds
        backoff_multiplier: Multiplier for backoff time after each retry
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            backoff = initial_backoff
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        time.sleep(backoff)
                        backoff *= backoff_multiplier
                    else:
                        # Final attempt failed, raise the exception
                        raise
            
            # Should never reach here, but just in case
            raise last_exception
        
        return wrapper
    return decorator

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def validate_ai_output(value: Any, field_name: str, expected_type: Optional[type] = None) -> bool:
    """
    Validate AI output before applying to database.
    
    Args:
        value: The value to validate
        field_name: Name of the field being validated
        expected_type: Expected Python type
        
    Returns:
        True if valid, False otherwise
    """
    # Null checks
    if value is None:
        return False
    
    # Empty value checks
    if isinstance(value, str) and not value.strip():
        return False
    if isinstance(value, (list, dict)) and not value:
        return False
    
    # Type validation
    if expected_type and not isinstance(value, expected_type):
        return False
    
    return True

def create_audit_log(
    db: Session,
    entity_type: str,
    entity_id: int,
    action: str,
    changes: Dict[str, Any],
    source: str = "USER",
    confidence: Optional[int] = None,
    user_id: Optional[int] = None,
    approval_status: Optional[str] = None,
    before_state: Optional[Dict[str, Any]] = None,
    after_state: Optional[Dict[str, Any]] = None,
    commit: bool = True
) -> AuditLog:
    """
    Create a comprehensive audit log entry.
    
    Args:
        db: Database session
        entity_type: Type of entity (e.g., "Item", "Category")
        entity_id: ID of the entity
        action: Action performed (CREATE, UPDATE, DELETE, SUGGEST, APPROVE, REJECT)
        changes: Dictionary of changes made
        source: Source of change (USER, AI_GENERATED, AI_SCRAPED)
        confidence: AI confidence score as integer 0–100
        user_id: ID of user who initiated the action
        approval_status: Explicit approval status; derived from confidence when omitted
                         for AI sources (auto_approved / pending / needs_review)
        before_state: State before changes
        after_state: State after changes
        commit: When True (default) the session is committed and refreshed after adding
                the entry.  Pass False when the caller is already inside a transaction
                and wants to control when the commit happens (add/flush only).
        
    Returns:
        Created AuditLog entry
    """
    # Store before/after states in the changes dict for compatibility with existing model
    extended_changes = {
        **changes,
        "before": before_state or {},
        "after": after_state or {},
    }
    
    # Determine approval status based on confidence, assuming confidence is an int 0-100
    if approval_status is None and source in ["AI_GENERATED", "AI_SCRAPED"] and confidence is not None:
        if confidence >= settings.AI_AUTO_APPLY_CONFIDENCE * 100:
            approval_status = "auto_approved"
        elif confidence >= settings.AI_MANUAL_REVIEW_THRESHOLD * 100:
            approval_status = "pending"
        else:
            approval_status = "needs_review"
    
    # Use previous_values for before state (existing field)
    audit = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        changes=extended_changes,
        previous_values=before_state or {},
        source=source,
        confidence=confidence,
        user_id=user_id,
        approval_status=approval_status
    )
    
    db.add(audit)
    if commit:
        db.commit()
        db.refresh(audit)
    else:
        db.flush()
    
    return audit

def scrape_item_task(item_id: int):
    """
    Background task to scrape item information from web sources.
    
    This task is triggered when AI suggests high-confidence product information
    that can be automatically retrieved from manufacturer or distributor websites.
    
    The actual scraping logic is part of process_item_image for now, but this
    provides a separate entry point for manual triggering or future enhancements.
    
    Args:
        item_id: ID of the item to scrape information for
    """
    db = SessionLocal()
    try:
        item = db.query(Item).filter(Item.id == item_id).first()
        if not item:
            logger.error(f"Item {item_id} not found for scraping.")
            return
        
        # Determine search query: prefer ocr_text if available, else name
        search_query = None
        pending = item.pending_changes or {}
        if pending.get('ocr_text') and pending['ocr_text'] != "pending":
            search_query = pending['ocr_text']
        elif item.name:
            search_query = item.name

        if not search_query:
            logger.warning(f"Item {item_id} has no suitable search query (name or ocr_text) for scraping.")
            return

        async def run_scrape():
            url = await ai_client.find_product_url(search_query)
            if url:
                scrape_result = await ai_client.scrape_url(url)
                return url, scrape_result
            return None, None

        url, scrape_result = asyncio.run(run_scrape())

        if scrape_result:
            # Save scraped URL
            updated_pending = dict(item.pending_changes or {})
            updated_pending['source_url'] = url

            import requests
            downloaded_docs = []

            # Helper to download and save
            def save_doc(doc_url, prefix="doc"):
                try:
                    timeout = settings_manager.get("scrape_timeout", 30)
                    resp = requests.get(doc_url, timeout=timeout)
                    if resp.status_code == 200:
                        import uuid
                        key = f"items/{item.id}/docs/{prefix}-{uuid.uuid4()}.pdf"
                        storage.upload_file(io.BytesIO(resp.content), key, "application/pdf", bucket_type="docs")

                        media_entry = Media(
                            item_id=item.id,
                            type="pdf",
                            s3_key=key,
                            metadata_json={"source_url": doc_url}
                        )
                        db.add(media_entry)
                        downloaded_docs.append(key)
                except Exception as e:
                    logger.error(f"Error downloading {doc_url}: {e}")

            if scrape_result.get('pdf_snapshot'):
                save_doc(scrape_result['pdf_snapshot'], "snapshot")

            for sheet in scrape_result.get('datasheets', []):
                save_doc(sheet, "datasheet")

            item.pending_changes = updated_pending

            create_audit_log(
                db=db,
                entity_type="Item",
                entity_id=item.id,
                action="SUGGEST",
                changes={"scraped_url": url, "docs": len(downloaded_docs)},
                source="AI_SCRAPED",
                confidence=100,
            )
            db.commit()
            logger.info(f"Successfully scraped item {item_id} from {url}")

    except Exception as e:
        logger.error(f"Error in scrape_item_task for item {item_id}: {e}")
        db.rollback()
        raise e
    finally:
        db.close()

def generate_thumbnails(image_bytes: bytes, item_id: int, original_filename: str):
    """
    Generate medium and thumbnail versions of the image and upload them.
    Returns a dict of {type: s3_key}.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        original_format = img.format
        content_type = f"image/{original_format.lower()}" if original_format else "image/jpeg"

        derived = {}

        # Sizes
        sizes = {
            "medium": (800, 800),
            "thumbnail": (200, 200)
        }

        import uuid
        base_name = original_filename.rsplit('/', 1)[-1]

        for size_name, dimensions in sizes.items():
            img_copy = img.copy()
            img_copy.thumbnail(dimensions)

            out_io = io.BytesIO()
            img_copy.save(out_io, format=original_format or 'JPEG')
            out_io.seek(0)

            key = f"items/{item_id}/{size_name}-{uuid.uuid4()}-{base_name}"
            storage.upload_file(out_io, key, content_type)
            derived[size_name] = key

        return derived
    except Exception as e:
        logger.error(f"Error generating thumbnails: {e}")
        return {}

def process_item_image(item_id: int, media_id: int):
    """
    Background task to process an item image.
    1. Download image from S3.
    2. Generate Thumbnails.
    3. OCR.
    4. Resistor ID.
    5. Update Item.
    6. If High Confidence -> Scrape.
    """
    db = SessionLocal()
    try:
        item = db.query(Item).filter(Item.id == item_id).first()
        media = db.query(Media).filter(Media.id == media_id).first()

        if not item or not media:
            logger.warning(f"Item {item_id} or Media {media_id} not found.")
            return

        # 1. Download Image
        try:
            file_stream = io.BytesIO()
            storage.s3_client.download_fileobj(storage.bucket_media, media.s3_key, file_stream)
            file_stream.seek(0)
            image_bytes = file_stream.read()
        except Exception as e:
            logger.error(f"Error downloading image: {e}")
            raise e

        # 2. Generate Thumbnails
        thumbnails = generate_thumbnails(image_bytes, item_id, media.s3_key)
        for size, key in thumbnails.items():
            new_media = Media(
                item_id=item.id,
                type="image",
                s3_key=key,
                metadata_json={"size": size, "original_id": media.id}
            )
            db.add(new_media)

        if thumbnails:
             db.commit()

        # 3. Call AI Services (Async wrapper)
        async def run_ai():
            ocr_task = ai_client.ocr_image(image_bytes)
            resistor_task = ai_client.identify_resistor(image_bytes)
            return await asyncio.gather(ocr_task, resistor_task, return_exceptions=True)

        results = asyncio.run(run_ai())
        ocr_result, resistor_result = results

        changes = {}
        ocr_text = None
        ocr_confidence = 0.0

        # Process OCR
        if isinstance(ocr_result, dict) and ocr_result.get('text'):
             ocr_text = ocr_result['text']
             ocr_confidence = ocr_result.get('confidence', 0.0)

             # If item is draft and has no name, use OCR text
             if item.is_draft and not item.name:
                 changes['name'] = ocr_text[:100] # Truncate
                 item.name = changes['name']
                 item.slug = item.name.lower().replace(" ", "-") # Update slug

             # Store full OCR in pending_changes
             pending = dict(item.pending_changes or {})
             pending['ocr_text'] = ocr_text
             item.pending_changes = pending
             changes['ocr_text'] = "pending"

             # Audit
             create_audit_log(
                db=db,
                entity_type="Item",
                entity_id=item.id,
                action="SUGGEST",
                changes={"ocr": "pending"},
                source="AI_GENERATED",
                confidence=int(ocr_confidence * 100),
                commit=False,
             )

        # Process Resistor
        if isinstance(resistor_result, dict) and resistor_result.get('is_resistor'):
            confidence = resistor_result.get('confidence', 0.0)
            resistance = resistor_result.get('resistance')
            tolerance = resistor_result.get('tolerance')

            pending = dict(item.pending_changes or {})
            pending['resistance'] = resistance
            pending['tolerance'] = tolerance
            item.pending_changes = pending

            source = "AI_SCRAPED" if confidence >= 0.95 else "AI_GENERATED"

            create_audit_log(
                db=db,
                entity_type="Item",
                entity_id=item.id,
                action="SUGGEST",
                changes={"resistance": resistance, "tolerance": tolerance},
                source=source,
                confidence=int(confidence * 100),
                commit=False,
            )

        db.commit()

        # 4. Scrape if high confidence (>= 0.95 or setting)
        threshold = settings_manager.get("ai_confidence_threshold", 0.95)

        if ocr_text and ocr_confidence >= threshold:
            async def run_scrape():
                url = await ai_client.find_product_url(ocr_text)
                if url:
                    scrape_result = await ai_client.scrape_url(url)
                    return url, scrape_result
                return None, None

            url, scrape_result = asyncio.run(run_scrape())

            if scrape_result:
                # Save scraped URL
                pending = dict(item.pending_changes or {})
                pending['source_url'] = url

                # Handle Datasheets/PDFs
                # Assuming scrape_result structure: {'datasheets': ['url1'], 'pdf_snapshot': 'url2'}
                import requests

                downloaded_docs = []

                # Helper to download and save
                def save_doc(doc_url, prefix="doc"):
                    try:
                        timeout = settings_manager.get("scrape_timeout", 30)
                        resp = requests.get(doc_url, timeout=timeout)
                        if resp.status_code == 200:
                            import uuid
                            key = f"items/{item.id}/docs/{prefix}-{uuid.uuid4()}.pdf"
                            storage.upload_file(io.BytesIO(resp.content), key, "application/pdf", bucket_type="docs")

                            media_entry = Media(
                                item_id=item.id,
                                type="pdf",
                                s3_key=key,
                                metadata_json={"source_url": doc_url}
                            )
                            db.add(media_entry)
                            downloaded_docs.append(key)
                    except Exception as e:
                        logger.error(f"Error downloading {doc_url}: {e}")

                if scrape_result.get('pdf_snapshot'):
                    save_doc(scrape_result['pdf_snapshot'], "snapshot")

                for sheet in scrape_result.get('datasheets', []):
                    save_doc(sheet, "datasheet")

                item.pending_changes = pending

                create_audit_log(
                    db=db,
                    entity_type="Item",
                    entity_id=item.id,
                    action="SUGGEST",
                    changes={"scraped_url": url, "docs": len(downloaded_docs)},
                    source="AI_SCRAPED",
                    confidence=100,
                    commit=False,
                )
                db.commit()

    except Exception as e:
        logger.error(f"Error processing item image: {e}")
        db.rollback()
        raise e
    finally:
        db.close()
