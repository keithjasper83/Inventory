#!/usr/bin/env python3
"""
Initialize SQLite database for development/testing
"""
from src.database import engine, Base

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created successfully")
