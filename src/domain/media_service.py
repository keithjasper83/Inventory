import io
import uuid
import logging
from PIL import Image
from typing import Dict, Any

logger = logging.getLogger(__name__)

class MediaService:
    """Domain service for handling media processing."""

    def __init__(self, storage_service):
        self.storage = storage_service

    def generate_thumbnails(self, image_bytes: bytes, item_id: int, original_filename: str) -> Dict[str, str]:
        """
        Generate medium and thumbnail versions of the image and upload them.
        Returns a dict of {type: s3_key}.
        """
        try:
            img = Image.open(io.BytesIO(image_bytes))

            # Convert image to RGB or RGBA for WebP compatibility
            if img.mode not in ("RGB", "RGBA"):
                if img.mode == "P" and "transparency" in img.info:
                    img = img.convert("RGBA")
                elif img.mode == "P" or img.mode == "L":
                    img = img.convert("RGB")
                else:
                    img = img.convert("RGB")

            content_type = "image/webp"
            derived = {}

            # Sizes
            sizes = {
                "medium": (800, 800),
                "thumbnail": (200, 200)
            }

            base_name = original_filename.rsplit('/', 1)[-1]

            # Handle removing extension from base_name to append .webp later
            if '.' in base_name:
                base_name_without_ext = base_name.rsplit('.', 1)[0]
            else:
                base_name_without_ext = base_name

            for size_name, dimensions in sizes.items():
                img_copy = img.copy()
                img_copy.thumbnail(dimensions)

                out_io = io.BytesIO()
                # Save as WebP with optimization and quality settings
                img_copy.save(out_io, format='WEBP', optimize=True, quality=85)
                out_io.seek(0)

                key = f"items/{item_id}/{size_name}-{uuid.uuid4()}-{base_name_without_ext}.webp"
                self.storage.upload_file(out_io, key, content_type)
                derived[size_name] = key

            return derived
        except Exception as e:
            logger.error(f"Error generating thumbnails: {e}")
            return {}
