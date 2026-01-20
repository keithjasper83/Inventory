from sqlalchemy.orm import Session
from src.database import SessionLocal, engine
from src.models import Location, Category, User
from src.auth import auth_service
from src.config import settings
import os
import getpass
import sys

def seed_data():
    db = SessionLocal()
    try:
        # Check if initialized
        if db.query(Location).count() > 0:
            print("Data already seeded.")
            return

        print("Seeding locations...")
        locations = ["DESK", "WALL"] + [f"BOX-{i:02d}" for i in range(1, 8)]
        for name in locations:
            slug = name.lower().replace(" ", "-")
            loc = Location(name=name, slug=slug, path=f"/{slug}/")
            db.add(loc)

        print("Seeding categories...")
        categories = ["Electronics", "Hardware", "Tools", "3D Printing", "Cables"]
        for name in categories:
            slug = name.lower().replace(" ", "-")
            cat = Category(name=name, slug=slug, schema={})
            db.add(cat)

        print("\nCreating admin user...")
        # Check if admin exists
        if not db.query(User).filter(User.username == "admin").first():
            # Get admin password from environment or prompt
            admin_password = os.environ.get("ADMIN_PASSWORD")
            
            if not admin_password:
                # Interactive mode - prompt for password
                if sys.stdin.isatty():
                    print("Please set a secure admin password.")
                    admin_password = getpass.getpass("Admin password: ")
                    confirm_password = getpass.getpass("Confirm password: ")
                    
                    if admin_password != confirm_password:
                        print("ERROR: Passwords do not match!")
                        sys.exit(1)
                    
                    if len(admin_password) < 8:
                        print("ERROR: Password must be at least 8 characters!")
                        sys.exit(1)
                else:
                    # Non-interactive mode (Docker) - use default but warn
                    print("WARNING: Using default admin password. CHANGE THIS IMMEDIATELY!")
                    print("Set ADMIN_PASSWORD environment variable for production deployment.")
                    admin_password = "admin"
            
            user = User(
                username="admin",
                password_hash=auth_service.get_password_hash(admin_password)
            )
            db.add(user)
            print("✓ Admin user created")

        db.commit()
        print("\nSeeding complete.")
        print("\nIMPORTANT: Login with username 'admin' and the password you set.")
    except Exception as e:
        print(f"Error seeding data: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
