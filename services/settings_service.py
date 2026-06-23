import sys
import os
from sqlalchemy.orm import Session
from typing import Optional

# Add project root to sys.path for module discovery
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from core.repositories.settings_repository import SettingsRepository

class SettingsService:
    def __init__(self, session: Session):
        self.repository = SettingsRepository(session)

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        setting = self.repository.get_setting(key)
        return setting.value if setting else default

    def set_setting(self, key: str, value: str):
        self.repository.set_setting(key, value)