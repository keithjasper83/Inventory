#!/usr/bin/env python3
"""
Seed development data for testing
"""
from sqlalchemy.orm import Session
from src.database import engine
from src.models import User, Category, Location, SystemSetting
import sys
sys.path.insert(0, '.')

def seed_data():
    with Session(engine) as db:
        # Check if data already exists
        if db.query(User).count() > 0:
            print("Database already has data, skipping seed")
            return
        
        # Add default user
        user = User(username="admin", password_hash="changeme")  # Change in production!
        db.add(user)
        
        # Add default categories
        categories = [
            Category(name="Electronics", slug="electronics", schema={}),
            Category(name="Components", slug="components", schema={}),
            Category(name="Tools", slug="tools", schema={})
        ]
        for cat in categories:
            db.add(cat)
        
        # Add default locations
        locations = [
            Location(name="Workshop", slug="workshop", path="/1/"),
            Location(name="Storage", slug="storage", path="/2/")
        ]
        for loc in locations:
            db.add(loc)
        
        # Add default system settings
        settings = [
            SystemSetting(key="ocr_confidence_threshold", value="0.8", description="Minimum confidence for OCR results"),
            SystemSetting(key="scrape_timeout", value="30", description="Timeout for web scraping in seconds"),
            SystemSetting(key="max_image_size_mb", value="10", description="Maximum image upload size in MB")
        ]
        for setting in settings:
            db.add(setting)
        
        db.commit()
        print("✓ Seed data added successfully")

if __name__ == "__main__":
    seed_data()
