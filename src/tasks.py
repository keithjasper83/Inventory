import time
from sqlalchemy.orm import Session
from src.database import SessionLocal
from src.models import Item, Media, AuditLog
from src.ai import ai_client
from src.storage import storage
from src.settings_manager import settings_manager
import asyncio
import io
from PIL import Image
from rq import get_current_job

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
        print(f"Error generating thumbnails: {e}")
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
            print(f"Item {item_id} or Media {media_id} not found.")
            return

        # 1. Download Image
        try:
            file_stream = io.BytesIO()
            storage.s3_client.download_fileobj(storage.bucket_media, media.s3_key, file_stream)
            file_stream.seek(0)
            image_bytes = file_stream.read()
        except Exception as e:
            print(f"Error downloading image: {e}")
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
             audit = AuditLog(
                entity_type="Item",
                entity_id=item.id,
                action="SUGGEST",
                changes={"ocr": "pending"},
                source="AI_GENERATED",
                confidence=int(ocr_confidence * 100)
             )
             db.add(audit)

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

            audit = AuditLog(
                entity_type="Item",
                entity_id=item.id,
                action="SUGGEST",
                changes={"resistance": resistance, "tolerance": tolerance},
                source=source,
                confidence=int(confidence * 100)
            )
            db.add(audit)

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
                        print(f"Error downloading {doc_url}: {e}")

                if scrape_result.get('pdf_snapshot'):
                    save_doc(scrape_result['pdf_snapshot'], "snapshot")

                for sheet in scrape_result.get('datasheets', []):
                    save_doc(sheet, "datasheet")

                item.pending_changes = pending

                audit = AuditLog(
                    entity_type="Item",
                    entity_id=item.id,
                    action="SUGGEST",
                    changes={"scraped_url": url, "docs": len(downloaded_docs)},
                    source="AI_SCRAPED",
                    confidence=100
                )
                db.add(audit)
                db.commit()

    except Exception as e:
        print(f"Error processing item image: {e}")
        db.rollback()
        raise e
    finally:
        db.close()
