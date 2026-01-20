import time
import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from src.database import SessionLocal
from src.models import Item, Media, AuditLog
from src.ai import ai_client
from src.storage import storage
from src.config import settings
import asyncio
import io
import requests
import uuid
from PIL import Image
from rq import get_current_job
from functools import wraps

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
INITIAL_BACKOFF = 2  # seconds
MAX_BACKOFF = 60  # seconds

def retry_with_backoff(max_retries=MAX_RETRIES, initial_backoff=INITIAL_BACKOFF):
    """
    Decorator to retry a function with exponential backoff.
    Handles transient errors in Redis/RQ jobs.
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
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries} failed for {func.__name__}: {str(e)}"
                    )
                    
                    if attempt < max_retries - 1:
                        sleep_time = min(backoff * (2 ** attempt), MAX_BACKOFF)
                        logger.info(f"Retrying in {sleep_time} seconds...")
                        time.sleep(sleep_time)
                    else:
                        logger.error(f"All retry attempts failed for {func.__name__}: {str(e)}")
            
            # If all retries failed, log to audit and raise
            raise last_exception
        return wrapper
    return decorator

def create_audit_log(
    db: Session,
    entity_type: str,
    entity_id: int,
    action: str,
    changes: Dict[str, Any],
    source: str,
    confidence: Optional[float] = None,
    user_id: Optional[int] = None,
    before_state: Optional[Dict] = None,
    after_state: Optional[Dict] = None,
    error_message: Optional[str] = None
) -> AuditLog:
    """
    Helper function to create comprehensive audit logs with pre/post states.
    
    Args:
        db: Database session
        entity_type: Type of entity (Item, Stock, etc.)
        entity_id: ID of the entity
        action: Action performed (CREATE, UPDATE, DELETE, SUGGEST, APPROVE, REJECT)
        changes: Dictionary of changes made
        source: Source of change (USER, AI_GENERATED, AI_SCRAPED)
        confidence: Confidence score (0-100) for AI operations
        user_id: ID of user who initiated the action
        before_state: State before changes
        after_state: State after changes
        error_message: Any error that occurred
    """
    # Enhance changes dict with before/after states
    enhanced_changes = {
        **changes,
        "before": before_state,
        "after": after_state
    }
    
    # Determine approval status based on confidence (confidence is 0-100 scale)
    approval_status = None
    if source in ["AI_GENERATED", "AI_SCRAPED"]:
        if confidence is not None:
            # Convert threshold from 0.0-1.0 to 0-100 scale for comparison
            auto_approve_threshold = settings.AI_AUTO_APPLY_CONFIDENCE * 100
            review_threshold = settings.AI_MANUAL_REVIEW_THRESHOLD * 100
            
            if confidence >= auto_approve_threshold:
                approval_status = "auto_approved"
            elif confidence >= review_threshold:
                approval_status = "pending"
            else:
                approval_status = "needs_review"
    
    audit = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        changes=enhanced_changes,
        source=source,
        confidence=confidence,
        user_id=user_id,
        approval_status=approval_status,
        error_message=error_message
    )
    db.add(audit)
    return audit

def validate_ai_output(data: Any, field_name: str, expected_type: type = None) -> bool:
    """
    Validate AI output to prevent null or invalid data.
    
    Args:
        data: Data to validate
        field_name: Name of the field being validated
        expected_type: Expected data type
    
    Returns:
        bool: True if valid, False otherwise
    """
    if data is None:
        logger.warning(f"AI output validation failed: {field_name} is None")
        return False
    
    if expected_type and not isinstance(data, expected_type):
        logger.warning(
            f"AI output validation failed: {field_name} expected {expected_type}, got {type(data)}"
        )
        return False
    
    # Check for empty strings or empty collections
    if isinstance(data, (str, list, dict)) and len(data) == 0:
        logger.warning(f"AI output validation failed: {field_name} is empty")
        return False
    
    return True

def get_db():
    db = SessionLocal()
    try:
        yield db
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
        print(f"Error generating thumbnails: {e}")
        return {}

def perform_scraping(item: Item, query_text: str, db: Session):
    """
    Performs the scraping logic: Find URL -> Scrape -> Download Docs -> Audit.
    Enhanced with validation and comprehensive audit logging.
    """
    logger.info(f"Scraping for item {item.id} with query: {query_text}")
    
    # Capture before state for audit
    before_state = {
        "source_url": item.pending_changes.get("source_url") if item.pending_changes else None
    }

    async def run_scrape():
        try:
            url = await ai_client.find_product_url(query_text)
            if url and validate_ai_output(url, "product_url", str):
                scrape_result = await ai_client.scrape_url(url)
                return url, scrape_result
            return None, None
        except Exception as e:
            logger.error(f"AI scraping failed: {str(e)}")
            raise

    try:
        url, scrape_result = asyncio.run(run_scrape())
    except Exception as e:
        error_msg = f"Scrape execution failed: {e}"
        logger.error(error_msg)
        # Log failure to audit
        create_audit_log(
            db=db,
            entity_type="Item",
            entity_id=item.id,
            action="SUGGEST",
            changes={"error": "scrape_failed"},
            source="AI_SCRAPED",
            confidence=0,
            before_state=before_state,
            error_message=error_msg
        )
        db.commit()
        return

    if scrape_result and validate_ai_output(scrape_result, "scrape_result", dict):
        # Save scraped URL
        pending = dict(item.pending_changes or {})
        pending['source_url'] = url

        downloaded_docs = []

        # Helper to download and save
        def save_doc(doc_url, prefix="doc"):
            try:
                if not validate_ai_output(doc_url, f"{prefix}_url", str):
                    return
                    
                resp = requests.get(doc_url, timeout=30)
                if resp.status_code == 200:
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
        
        # Capture after state
        after_state = {
            "source_url": url,
            "docs_downloaded": len(downloaded_docs)
        }

        # Create comprehensive audit log
        create_audit_log(
            db=db,
            entity_type="Item",
            entity_id=item.id,
            action="SUGGEST",
            changes={"scraped_url": url, "docs": len(downloaded_docs)},
            source="AI_SCRAPED",
            confidence=100,
            before_state=before_state,
            after_state=after_state
        )
        db.commit()
        logger.info(f"Successfully scraped item {item.id}: {url}, {len(downloaded_docs)} docs")

@retry_with_backoff(max_retries=MAX_RETRIES)
def scrape_item_task(item_id: int):
    """
    Task to explicitly scrape for an item using its Name or OCR text.
    Enhanced with retry logic and better error handling.
    """
    db = SessionLocal()
    try:
        item = db.query(Item).filter(Item.id == item_id).first()
        if not item:
            logger.error(f"Item {item_id} not found.")
            return

        query_text = item.name

        # If no name, try to check pending changes for OCR
        if not query_text and item.pending_changes:
            query_text = item.pending_changes.get('ocr_text')

        # If still nothing, abort
        if not query_text:
            logger.warning(f"No text available to scrape for item {item_id}")
            return

        perform_scraping(item, query_text, db)

    except Exception as e:
        logger.error(f"Error in scrape_item_task for item {item_id}: {str(e)}")
        raise  # Re-raise to trigger retry
    finally:
        db.close()

@retry_with_backoff(max_retries=MAX_RETRIES)
def process_item_image(item_id: int, media_id: int):
    """
    Background task to process an item image.
    1. Download image from S3.
    2. Generate Thumbnails.
    3. OCR.
    4. Resistor ID.
    5. Update Item.
    6. If High Confidence -> Scrape.
    
    Enhanced with retry logic, validation, and comprehensive audit logging.
    """
    db = SessionLocal()
    try:
        item = db.query(Item).filter(Item.id == item_id).first()
        media = db.query(Media).filter(Media.id == media_id).first()

        if not item or not media:
            logger.error(f"Item {item_id} or Media {media_id} not found.")
            return
        
        # Capture before state for audit
        before_state = {
            "name": item.name,
            "slug": item.slug,
            "pending_changes": dict(item.pending_changes or {})
        }

        # 1. Download Image
        try:
            file_stream = io.BytesIO()
            storage.s3_client.download_fileobj(storage.bucket_media, media.s3_key, file_stream)
            file_stream.seek(0)
            image_bytes = file_stream.read()
        except Exception as e:
            error_msg = f"Error downloading image: {e}"
            logger.error(error_msg)
            create_audit_log(
                db=db,
                entity_type="Item",
                entity_id=item.id,
                action="SUGGEST",
                changes={"error": "image_download_failed"},
                source="AI_GENERATED",
                confidence=0,
                before_state=before_state,
                error_message=error_msg
            )
            db.commit()
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

        # Process OCR with validation
        if isinstance(ocr_result, dict) and ocr_result.get('text'):
             ocr_text = ocr_result['text']
             ocr_confidence = ocr_result.get('confidence', 0.0)  # 0.0-1.0 scale
             
             # Validate OCR output
             if not validate_ai_output(ocr_text, "ocr_text", str):
                 logger.warning(f"Invalid OCR output for item {item.id}")
                 ocr_text = None
                 ocr_confidence = 0.0

             if ocr_text:
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
                    confidence=int(ocr_confidence * 100),  # Convert to 0-100 scale
                    before_state=before_state,
                    after_state={"ocr_text": ocr_text[:100]}
                 )

        # Process Resistor with validation
        if isinstance(resistor_result, dict) and resistor_result.get('is_resistor'):
            confidence = resistor_result.get('confidence', 0.0)  # 0.0-1.0 scale
            resistance = resistor_result.get('resistance')
            tolerance = resistor_result.get('tolerance')
            
            # Validate resistor data
            if validate_ai_output(resistance, "resistance") and validate_ai_output(tolerance, "tolerance"):
                pending = dict(item.pending_changes or {})
                pending['resistance'] = resistance
                pending['tolerance'] = tolerance
                item.pending_changes = pending

                # Determine source based on confidence (comparing 0.0-1.0 scale values)
                source = "AI_SCRAPED" if confidence >= settings.AI_AUTO_APPLY_CONFIDENCE else "AI_GENERATED"

                create_audit_log(
                    db=db,
                    entity_type="Item",
                    entity_id=item.id,
                    action="SUGGEST",
                    changes={"resistance": resistance, "tolerance": tolerance},
                    source=source,
                    confidence=int(confidence * 100),  # Convert to 0-100 scale for storage
                    before_state=before_state,
                    after_state={"resistance": resistance, "tolerance": tolerance}
                )
            else:
                logger.warning(f"Invalid resistor data for item {item.id}")

        db.commit()
        
        # Capture final state for logging
        after_state = {
            "name": item.name,
            "slug": item.slug,
            "pending_changes": dict(item.pending_changes or {})
        }
        logger.info(f"Successfully processed item {item.id}, OCR confidence: {ocr_confidence}")

        # 4. Scrape if high confidence (compare 0.0-1.0 scale values)
        if ocr_text and ocr_confidence >= settings.AI_AUTO_APPLY_CONFIDENCE:
            logger.info(f"High confidence OCR ({ocr_confidence}), triggering scraping for item {item.id}")
            perform_scraping(item, ocr_text, db)

    except Exception as e:
        error_msg = f"Error processing item image: {e}"
        logger.error(error_msg)
        db.rollback()
        # Log error to audit
        create_audit_log(
            db=db,
            entity_type="Item",
            entity_id=item_id,
            action="SUGGEST",
            changes={"error": "processing_failed"},
            source="AI_GENERATED",
            confidence=0,
            error_message=error_msg
        )
        db.commit()
        raise e
    finally:
        db.close()
