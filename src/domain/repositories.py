"""Repository interfaces and implementations for data access layer.

Following the repository pattern to separate data access from business logic.
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import or_, text
from src.models import Item, Category, Location, Stock, Media, AuditLog


class ItemRepository:
    """Repository for Item entity operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, item_id: int) -> Optional[Item]:
        """Get item by ID."""
        return self.db.query(Item).filter(Item.id == item_id).first()
    
    def get_by_slug(self, slug: str) -> Optional[Item]:
        """Get item by slug."""
        return self.db.query(Item).filter(Item.slug == slug).first()
    
    def search_by_text(self, query: str) -> List[Item]:
        """Search items using PostgreSQL FTS."""
        try:
            search_query = text("search_vector @@ plainto_tsquery('english', :q)")
            return self.db.query(Item).filter(search_query).params(q=query).all()
        except Exception:
            # Fallback for SQLite or error
            return self.db.query(Item).filter(Item.name.ilike(f"%{query}%")).all()
    
    def create(self, item: Item) -> Item:
        """Create a new item."""
        self.db.add(item)
        self.db.flush()
        return item
    
    def update(self, item: Item) -> Item:
        """Update an existing item."""
        self.db.add(item)
        self.db.flush()
        return item
    
    def delete(self, item: Item) -> None:
        """Delete an item."""
        self.db.delete(item)
        self.db.flush()


class CategoryRepository:
    """Repository for Category entity operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, category_id: int) -> Optional[Category]:
        """Get category by ID."""
        return self.db.query(Category).filter(Category.id == category_id).first()
    
    def get_by_slug(self, slug: str) -> Optional[Category]:
        """Get category by slug."""
        return self.db.query(Category).filter(Category.slug == slug).first()
    
    def get_all(self) -> List[Category]:
        """Get all categories."""
        return self.db.query(Category).all()
    
    def create(self, category: Category) -> Category:
        """Create a new category."""
        self.db.add(category)
        self.db.flush()
        return category


class LocationRepository:
    """Repository for Location entity operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, location_id: int) -> Optional[Location]:
        """Get location by ID."""
        return self.db.query(Location).filter(Location.id == location_id).first()
    
    def get_by_slug(self, slug: str) -> Optional[Location]:
        """Get location by slug."""
        return self.db.query(Location).filter(Location.slug == slug).first()
    
    def get_all(self) -> List[Location]:
        """Get all locations."""
        return self.db.query(Location).all()
    
    def create(self, location: Location) -> Location:
        """Create a new location."""
        self.db.add(location)
        self.db.flush()
        return location


class MediaRepository:
    """Repository for Media entity operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, media_id: int) -> Optional[Media]:
        """Get media by ID."""
        return self.db.query(Media).filter(Media.id == media_id).first()
    
    def get_by_item(self, item_id: int) -> List[Media]:
        """Get all media for an item."""
        return self.db.query(Media).filter(Media.item_id == item_id).all()
    
    def create(self, media: Media) -> Media:
        """Create a new media entry."""
        self.db.add(media)
        self.db.flush()
        return media


class AuditLogRepository:
    """Repository for AuditLog entity operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, audit_log: AuditLog) -> AuditLog:
        """Create a new audit log entry."""
        self.db.add(audit_log)
        self.db.flush()
        return audit_log
    
    def get_by_entity(self, entity_type: str, entity_id: int) -> List[AuditLog]:
        """Get all audit logs for an entity."""
        return self.db.query(AuditLog).filter(
            AuditLog.entity_type == entity_type,
            AuditLog.entity_id == entity_id
        ).order_by(AuditLog.timestamp.desc()).all()


class StockRepository:
    """Repository for Stock entity operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get(self, item_id: int, location_id: int) -> Optional[Stock]:
        """Get stock for item at location."""
        return self.db.query(Stock).filter(
            Stock.item_id == item_id,
            Stock.location_id == location_id
        ).first()
    
    def get_by_item(self, item_id: int) -> List[Stock]:
        """Get all stock entries for an item."""
        return self.db.query(Stock).filter(Stock.item_id == item_id).all()
    
    def create(self, stock: Stock) -> Stock:
        """Create a new stock entry."""
        self.db.add(stock)
        self.db.flush()
        return stock
    
    def update(self, stock: Stock) -> Stock:
        """Update a stock entry."""
        self.db.add(stock)
        self.db.flush()
        return stock
