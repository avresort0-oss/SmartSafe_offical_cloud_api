import sys
import os
from typing import Optional

# Add project root to sys.path for module discovery
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from sqlalchemy.orm import Session

from core.repository import BaseRepository
from core.models.app_setting import AppSetting


class SettingsRepository(BaseRepository[AppSetting]):
    def __init__(self, session: Session):
        super().__init__(session, AppSetting)

    def get_setting(self, key: str) -> Optional[AppSetting]:
        return self.session.query(AppSetting).filter_by(key=key).first()

    def set_setting(self, key: str, value: str) -> AppSetting:
        setting = self.get_setting(key)
        if setting:
            setting.value = value
        else:
            setting = AppSetting(key=key, value=value)
            self.session.add(setting)
        self.session.commit()
        self.session.refresh(setting)
        return setting