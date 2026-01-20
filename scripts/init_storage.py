#!/usr/bin/env python3
"""
Storage initialization script for Jules Inventory Platform.
Creates S3-compatible storage buckets (MinIO) if they don't exist.
"""
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.storage import storage
from src.config import settings

def init_storage():
    """Initialize S3-compatible storage buckets."""
    print("Initializing S3-compatible storage...")
    
    try:
        # Check connectivity
        print(f"Connecting to S3 endpoint: {settings.S3_ENDPOINT_URL}")
        
        # Use the built-in ensure_buckets method
        storage.ensure_buckets()
        
        print(f"✓ Verified/created bucket: {settings.BUCKET_MEDIA}")
        print(f"✓ Verified/created bucket: {settings.BUCKET_DOCS}")
        print("Storage initialization complete.")
        return True
        
    except Exception as e:
        print(f"✗ Storage initialization failed: {e}")
        print("\nPlease ensure:")
        print("  1. MinIO or S3-compatible service is running")
        print(f"  2. Endpoint is accessible: {settings.S3_ENDPOINT_URL}")
        print("  3. Credentials are correct in .env")
        print("\nYou can skip storage initialization and configure it later.")
        return False

if __name__ == "__main__":
    success = init_storage()
    sys.exit(0 if success else 1)
