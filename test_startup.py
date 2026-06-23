from core.database import init_db, SessionLocal
from services.settings_service import SettingsService
from dotenv import load_dotenv
load_dotenv(".env")
import logging

logging.basicConfig(level=logging.INFO)

try:
    print("init_db...")
    init_db()
    print("SessionLocal...")
    db_session = SessionLocal()
    print("SettingsService...")
    settings_service = SettingsService(db_session)
    # Check if SettingsService executes a query
    val = settings_service.get_setting("MOCK_ENABLED")
    print(f"MOCK_ENABLED: {val}")
    print("done")
except Exception as e:
    logging.exception("Failed")
