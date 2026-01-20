from sqlalchemy.orm import Session
from src.database import SessionLocal, engine
from src.models import Location, Category, User
from src.auth import auth_service
from src.config import settings

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

        print("Creating admin user...")
        # Check if admin exists
        if not db.query(User).filter(User.username == "admin").first():
            user = User(
                username="admin",
                password_hash=auth_service.get_password_hash("admin") # Default password
            )
            db.add(user)

        db.commit()
        print("Seeding complete.")
    except Exception as e:
        print(f"Error seeding data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
