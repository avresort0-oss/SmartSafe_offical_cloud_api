import os
from dotenv import load_dotenv
load_dotenv(".env")
from core.database import init_db
import logging
logging.basicConfig(level=logging.INFO)
print("Initializing database tables...")
init_db()
print("Done.")
