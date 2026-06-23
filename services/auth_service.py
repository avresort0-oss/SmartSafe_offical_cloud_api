import os
import secrets
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import argon2 # assuming argon2-cffi is available for enterprise grade hashing

from core.models.api_key import ApiKey
from core.models.workspace import Workspace

logger = logging.getLogger(__name__)
ph = argon2.PasswordHasher()

class AuthService:
    """
    Handles API key generation, hashing, and validation for multi-tenant isolation.
    """
    
    @staticmethod
    def generate_api_key(workspace_id: str, label: str, expires_in_days: Optional[int] = None) -> Tuple[str, ApiKey]:
        """
        Generates a new API key for a workspace.
        Returns a tuple of (raw_key, api_key_model).
        The raw_key should only be shown ONCE to the user.
        """
        # 1. Create a secure random key
        prefix = "ss_live_"
        random_part = secrets.token_urlsafe(32)
        raw_key = f"{prefix}{random_part}"
        
        # 2. Hash the key for storage
        key_hash = ph.hash(raw_key)
        
        # 3. Create the model
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
            
        api_key = ApiKey(
            workspace_id=workspace_id,
            label=label,
            prefix=prefix,
            key_hash=key_hash,
            expires_at=expires_at,
            is_active=True
        )
        
        return raw_key, api_key

    @staticmethod
    def validate_api_key(session: Session, raw_key: str) -> Optional[Workspace]:
        """
        Validates a raw API key and returns the associated Workspace if valid.
        """
        if not raw_key or not raw_key.startswith("ss_live_"):
            return None
            
        prefix = raw_key[:8]
        keys = session.query(ApiKey).filter(ApiKey.prefix == prefix, ApiKey.is_active == True).all()
        
        for key in keys:
            try:
                ph.verify(key.key_hash, raw_key)
                # Check expiration
                if key.expires_at and key.expires_at < datetime.now(timezone.utc):
                    logger.warning(f"API Key {key.id} expired.")
                    return None
                
                # Update last used
                key.last_used_at = datetime.now(timezone.utc)
                session.commit()
                return key.workspace
            except argon2.exceptions.VerifyMismatchError:
                continue
            except Exception as e:
                logger.error(f"Unexpected error validating API key: {e}")
                continue
                
        return None
