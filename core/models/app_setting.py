import os
import sys
from sqlalchemy import Column, String

# Add project root to sys.path for module discovery
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from core.database import Base

class AppSetting(Base):
    __tablename__ = "app_settings"
    key = Column(String, primary_key=True, index=True)
    value = Column(String, nullable=True)