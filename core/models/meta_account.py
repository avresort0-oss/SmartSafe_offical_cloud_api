import os
import sys
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path
from cryptography.fernet import Fernet
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from core.database import Base
from core.models.base import AuditMixin

logger = logging.getLogger(__name__)

def _get_or_create_encryption_key() -> bytes:
    """
    Retrieves or creates the secret key for encrypting Meta API access tokens.
    Stored securely in ~/.smartsafe/secret.key.
    """
    key_dir = Path.home() / ".smartsafe"
    key_file = key_dir / "secret.key"
    
    try:
        if not key_file.exists():
            key_dir.mkdir(parents=True, exist_ok=True)
            key = Fernet.generate_key()
            key_file.write_bytes(key)
            if os.name != 'nt': # Avoid chmod crash on Windows if strict POSIX isn't available
                os.chmod(key_file, 0o600) 
            logger.info(f"Generated new Meta API encryption key at {key_file}")
            return key
        return key_file.read_bytes()
    except Exception as e:
        logger.error(f"Failed to load/create encryption key at {key_file}: {e}")
        # Fallback for dev environments if home dir is inaccessible
        fallback_key = os.getenv("META_ENCRYPTION_KEY")
        if fallback_key:
            return fallback_key.encode('utf-8')
        raise RuntimeError("CRITICAL: Cannot initialize Meta API encryption key.")

_ENCRYPTION_KEY = _get_or_create_encryption_key()
_FERNET = Fernet(_ENCRYPTION_KEY)

class MetaAccount(AuditMixin, Base):
    __tablename__ = "meta_accounts"
    display_name = Column(String, nullable=False)
    phone_number_id = Column(String, nullable=False, index=True)
    _access_token_encrypted = Column("access_token", String, nullable=False)
    waba_id = Column(String, nullable=False)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False)

    # Cached from API (refreshed on dashboard load)
    display_phone = Column(String, default="")
    verified_name = Column(String, default="")
    quality_rating = Column(String, default="UNKNOWN")  # "GREEN", "YELLOW", "RED", "UNKNOWN"
    api_status = Column(String, default="UNKNOWN")      # "CONNECTED", "DISCONNECTED", "UNKNOWN"

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    last_synced_at = Column(DateTime, nullable=True)

    @property
    def access_token(self) -> str:
        """Decrypts and returns the Meta API access token seamlessly."""
        if not self._access_token_encrypted:
            return ""
        return _FERNET.decrypt(self._access_token_encrypted.encode('utf-8')).decode('utf-8')

    @access_token.setter
    def access_token(self, plain_text_token: str):
        """Encrypts the Meta API access token before storage."""
        if plain_text_token:
            self._access_token_encrypted = _FERNET.encrypt(plain_text_token.encode('utf-8')).decode('utf-8')
        else:
            self._access_token_encrypted = ""