from datetime import datetime
from typing import List, Optional
import os
from sqlalchemy import String, Integer, Boolean, ForeignKey, DateTime, Text, Index, Computed, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from src.database import Base
from src.config import settings

# Handle TSVECTOR for non-Postgres environments (e.g. tests)
try:
    from sqlalchemy.dialects.postgresql import TSVECTOR, JSONB
except ImportError:
    TSVECTOR = Text
    JSONB = JSON

if "sqlite" in settings.DATABASE_URL or os.environ.get("TEST_MODE"):
    TSVECTOR = Text
    # SQLite doesn't support JSONB, so we map it to generic JSON or Text if needed,
    # but SQLAlchemy's JSON type handles serialization for SQLite.
    # However, we imported JSONB from postgresql dialect which might cause issues if used directly.
    # We used JSON in the code, which is good.
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

class Location(Base):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, index=True)
    slug: Mapped[str] = mapped_column(String, unique=True, index=True)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("locations.id"), nullable=True)
    path: Mapped[str] = mapped_column(String, index=True, default="/") # Materialized path e.g. /1/5/

    parent: Mapped[Optional["Location"]] = relationship("Location", remote_side=[id], back_populates="children")
    children: Mapped[List["Location"]] = relationship("Location", back_populates="parent")
    stock: Mapped[List["Stock"]] = relationship("Stock", back_populates="location")

class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    slug: Mapped[str] = mapped_column(String, unique=True, index=True)
    schema: Mapped[dict] = mapped_column(JSON, server_default='{}')

    items: Mapped[List["Item"]] = relationship("Item", back_populates="category")

class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, index=True, nullable=True) # Can be null if draft
    slug: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=True)
    category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id"), nullable=True)
    data: Mapped[dict] = mapped_column(JSON, server_default='{}')
    pending_changes: Mapped[dict] = mapped_column(JSON, server_default='{}') # Stores AI suggestions for review
    is_draft: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    # Full Text Search Vector
    # Conditional definition for compatibility
    if "sqlite" not in settings.DATABASE_URL and not os.environ.get("TEST_MODE"):
        search_vector: Mapped[str] = mapped_column(TSVECTOR, Computed("to_tsvector('english', coalesce(name, '') || ' ' || coalesce(data::text, ''))", persisted=True))
        __table_args__ = (
            Index("ix_items_search_vector", "search_vector", postgresql_using="gin"),
        )
    else:
        # Mock column for SQLite to avoid attribute errors
        search_vector: Mapped[str] = mapped_column(String, nullable=True)

    category: Mapped[Optional["Category"]] = relationship("Category", back_populates="items")
    stock: Mapped[List["Stock"]] = relationship("Stock", back_populates="item")
    media: Mapped[List["Media"]] = relationship("Media", back_populates="item")

class Stock(Base):
    __tablename__ = "stock"

    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), primary_key=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), primary_key=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)

    item: Mapped["Item"] = relationship("Item", back_populates="stock")
    location: Mapped["Location"] = relationship("Location", back_populates="stock")

class Media(Base):
    __tablename__ = "media"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"))
    type: Mapped[str] = mapped_column(String) # image, pdf
    s3_key: Mapped[str] = mapped_column(String)
    metadata_json: Mapped[dict] = mapped_column(JSON, server_default='{}') # Renamed to avoid confusion with MetaData
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    item: Mapped["Item"] = relationship("Item", back_populates="media")

class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String) # Item, Stock, etc.
    entity_id: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String) # CREATE, UPDATE, DELETE, SUGGEST, UNDO
    changes: Mapped[dict] = mapped_column(JSON)
    previous_values: Mapped[dict] = mapped_column(JSON, server_default='{}')
    is_undone: Mapped[bool] = mapped_column(Boolean, default=False)
    confidence: Mapped[Optional[float]] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String) # USER, AI_GENERATED, AI_SCRAPED
    timestamp: Mapped[datetime] = mapped_column(server_default=func.now())

class SystemSetting(Base):
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[dict] = mapped_column(JSON) # Store as JSON for type flexibility
    description: Mapped[str] = mapped_column(String, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
