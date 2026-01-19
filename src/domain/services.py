"""Domain services encapsulating business logic for bounded contexts.

Following DDD principles, domain services contain business logic that doesn't
naturally fit within a single entity.
"""
from typing import Optional, List, Dict, Any
import uuid
from sqlalchemy.orm import Session

from src.models import Item, Category, Location, Stock, Media, AuditLog
from src.domain.repositories import (
    ItemRepository, CategoryRepository, LocationRepository,
    StockRepository, MediaRepository, AuditLogRepository
)


class ItemService:
    """Domain service for Item bounded context."""
    
    def __init__(self, db: Session):
        self.db = db
        self.item_repo = ItemRepository(db)
        self.stock_repo = StockRepository(db)
        self.media_repo = MediaRepository(db)
        self.audit_repo = AuditLogRepository(db)
    
    def create_item(
        self,
        name: Optional[str],
        location_id: int,
        category_id: Optional[int],
        quantity: int,
        data: Dict[str, Any]
    ) -> Item:
        """Create a new inventory item.
        
        Business rules:
        - Item is draft if name is missing
        - Slug is generated from name if provided
        - Stock entry is created automatically
        - Audit log is created
        """
        is_draft = name is None
        slug = None
        
        if name:
            base_slug = name.lower().replace(" ", "-")
            slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"
        
        item = Item(
            name=name,
            slug=slug,
            category_id=category_id,
            is_draft=is_draft,
            data=data
        )
        
        item = self.item_repo.create(item)
        
        # Create stock entry
        stock = Stock(item_id=item.id, location_id=location_id, quantity=quantity)
        self.stock_repo.create(stock)
        
        # Create audit log
        audit = AuditLog(
            entity_type="Item",
            entity_id=item.id,
            action="CREATE",
            changes={"name": name, "is_draft": is_draft},
            source="USER"
        )
        self.audit_repo.create(audit)
        
        self.db.commit()
        return item
    
    def get_item_by_slug(self, slug: str) -> Optional[Item]:
        """Get item by slug."""
        return self.item_repo.get_by_slug(slug)
    
    def get_item_by_id(self, item_id: int) -> Optional[Item]:
        """Get item by ID."""
        return self.item_repo.get_by_id(item_id)
    
    def approve_pending_changes(self, item_id: int) -> Item:
        """Approve pending AI suggestions.
        
        Business rules:
        - Merge pending_changes into data
        - Clear pending_changes
        - Create audit log
        """
        item = self.item_repo.get_by_id(item_id)
        if not item:
            raise ValueError(f"Item {item_id} not found")
        
        if item.pending_changes:
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
            self.audit_repo.create(audit)
            self.db.commit()
        
        return item
    
    def reject_pending_changes(self, item_id: int) -> Item:
        """Reject pending AI suggestions.
        
        Business rules:
        - Clear pending_changes
        - Create audit log
        """
        item = self.item_repo.get_by_id(item_id)
        if not item:
            raise ValueError(f"Item {item_id} not found")
        
        if item.pending_changes:
            item.pending_changes = {}
            
            audit = AuditLog(
                entity_type="Item",
                entity_id=item.id,
                action="REJECT",
                changes={},
                source="USER"
            )
            self.audit_repo.create(audit)
            self.db.commit()
        
        return item
    
    def get_media_with_urls(self, item: Item, storage_service) -> List[Dict[str, Any]]:
        """Get media list with presigned URLs."""
        media_list = []
        for m in item.media:
            url = storage_service.get_presigned_url(m.s3_key)
            media_list.append({
                "type": m.type,
                "s3_key": m.s3_key,
                "url": url,
                "metadata": m.metadata_json
            })
        return media_list


class LocationService:
    """Domain service for Location bounded context."""
    
    def __init__(self, db: Session):
        self.db = db
        self.location_repo = LocationRepository(db)
    
    def get_all_locations(self) -> List[Location]:
        """Get all locations."""
        return self.location_repo.get_all()
    
    def create_location(self, name: str, parent_id: Optional[int] = None) -> Location:
        """Create a new location.
        
        Business rules:
        - Slug is generated from name
        - Ensure unique slug by appending UUID if needed
        """
        slug = name.lower().replace(" ", "-")
        
        # Ensure unique slug
        if self.location_repo.get_by_slug(slug):
            slug = f"{slug}-{uuid.uuid4().hex[:4]}"
        
        location = Location(name=name, slug=slug, parent_id=parent_id)
        location = self.location_repo.create(location)
        self.db.commit()
        
        return location


class CategoryService:
    """Domain service for Category bounded context."""
    
    def __init__(self, db: Session):
        self.db = db
        self.category_repo = CategoryRepository(db)
    
    def get_all_categories(self) -> List[Category]:
        """Get all categories."""
        return self.category_repo.get_all()
    
    def get_category_by_id(self, category_id: int) -> Optional[Category]:
        """Get category by ID."""
        return self.category_repo.get_by_id(category_id)
    
    def create_category(self, name: str, schema: Dict[str, Any]) -> Category:
        """Create a new category.
        
        Business rules:
        - Slug is generated from name
        - Ensure unique slug by appending UUID if needed
        """
        slug = name.lower().replace(" ", "-")
        
        # Ensure unique slug
        if self.category_repo.get_by_slug(slug):
            slug = f"{slug}-{uuid.uuid4().hex[:4]}"
        
        category = Category(name=name, slug=slug, schema=schema)
        category = self.category_repo.create(category)
        self.db.commit()
        
        return category


class SearchService:
    """Domain service for Search bounded context."""
    
    def __init__(self, db: Session):
        self.db = db
        self.item_repo = ItemRepository(db)
    
    def search_items(self, query: str) -> List[Item]:
        """Search items using FTS.
        
        Business rules:
        - Use PostgreSQL FTS if available
        - Fallback to ILIKE for SQLite
        """
        return self.item_repo.search_by_text(query)
    
    def find_exact_slug(self, query: str) -> Optional[Item]:
        """Find item by exact slug match."""
        return self.item_repo.get_by_slug(query)
