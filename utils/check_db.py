import sys
import os
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.database import engine

def check_db():
    print("Checking Database connectivity...")
    try:
        # Try to connect and execute a simple query
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            print("Successfully connected to the database.")
            return True
    except Exception as e:
        print(f"Database connectivity failed: {e}")
        return False

if __name__ == "__main__":
    if check_db():
        sys.exit(0)
    else:
        sys.exit(1)
