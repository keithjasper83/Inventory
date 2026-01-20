from src.database import engine, Base
from src.models import *

def init_db():
    print("Creating tables for SQLite...")
    Base.metadata.create_all(bind=engine)
    print("Tables created.")

if __name__ == "__main__":
    init_db()
