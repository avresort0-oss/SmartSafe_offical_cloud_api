import sys
import os
import logging
import threading
import time
import random
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Callable, Tuple

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from sqlalchemy.orm import Session
from core.database import SessionLocal
from core.models.meta_account import MetaAccount
from core.repositories.meta_account_repository import MetaAccountRepository
from services.meta_cloud_service import MetaCloudService, MessageResultDTO

logger = logging.getLogger(__name__)

# --- DTOs API Boundaries ---

@dataclass
class MetaAccountDTO:
    id: str
    display_name: str
    phone_number_id: str
    waba_id: str
    display_phone: str
    verified_name: str
    quality_rating: str
    api_status: str
    is_active: bool
    workspace_id: str
    last_synced_at: Optional[datetime] = None
    access_token: Optional[str] = None

@dataclass
class MetaAccountCreateDTO:
    display_name: str
    phone_number_id: str
    access_token: str
    waba_id: str
    workspace_id: str

@dataclass
class SendMessageDTO:
    account_id: str
    to: str
    message_type: str
    text_body: str = ""
    template_name: str = ""
    template_language: str = "en_US"
    template_components: Optional[List] = None


# --- Business Logic Service ---

class MetaAccountService:
    """
    Orchestrates business logic for Meta Accounts, mapping local DB states
    to the official remote Meta Graph API.

    Design note: All DB operations open short-lived SessionLocal() sessions internally
    to ensure thread-safety (bulk_send runs in a background thread). The constructor
    session parameter is kept for API compatibility but is intentionally not used.
    """
    def __init__(self, session: Session, cloud_service: MetaCloudService):
        # NOTE: session is accepted for API compatibility but all methods use
        # short-lived SessionLocal() sessions for thread-safety. Do not use self.session
        # for DB operations — open a new session with SessionLocal() instead.
        self.cloud_service = cloud_service

    def _to_dto(self, account: MetaAccount) -> MetaAccountDTO:
        """Transforms SQLAlchemy model to a strictly typed DTO."""
        return MetaAccountDTO(
            id=account.id,
            display_name=account.display_name,
            phone_number_id=account.phone_number_id,
            waba_id=account.waba_id,
            display_phone=account.display_phone,
            verified_name=account.verified_name,
            quality_rating=account.quality_rating,
            api_status=account.api_status,
            is_active=account.is_active,
            workspace_id=account.workspace_id,
            last_synced_at=account.last_synced_at,
            access_token=account.access_token
        )

    def get_accounts(self, workspace_id: str, active_only: bool = True) -> List[MetaAccountDTO]:
        with SessionLocal() as session:
            repo = MetaAccountRepository(session)
            accounts = repo.get_by_workspace(workspace_id, active_only)
            return [self._to_dto(acc) for acc in accounts]

    def add_account(self, dto: MetaAccountCreateDTO) -> Tuple[Optional[MetaAccountDTO], Optional[str]]:
        """Validates credentials against Meta API and persists safely to the DB."""
        # 1. Verify via Meta API first
        phone_info, error = self.cloud_service.get_phone_info(dto.phone_number_id, dto.access_token)
        if error:
            return None, f"Meta API Verification Failed: {error}"

        # 2. Create in DB with automated property-level encryption
        new_account = MetaAccount(
            display_name=dto.display_name,
            phone_number_id=dto.phone_number_id,
            waba_id=dto.waba_id,
            workspace_id=dto.workspace_id,
            display_phone=phone_info.display_phone_number if phone_info else "",
            verified_name=phone_info.verified_name if phone_info else "",
            quality_rating=phone_info.quality_rating if phone_info else "UNKNOWN",
            api_status=phone_info.api_status if phone_info else "UNKNOWN"
        )
        new_account.access_token = dto.access_token # Encrypted setter intercept

        with SessionLocal() as session:
            repo = MetaAccountRepository(session)
            repo.add(new_account)
            return self._to_dto(new_account), None

    def remove_account(self, account_id: str) -> bool:
        """Soft deletes the account to preserve related message history."""
        with SessionLocal() as session:
            repo = MetaAccountRepository(session)
            return repo.soft_delete(account_id)

    def refresh_account_status(self, account_id: str) -> Optional[MetaAccountDTO]:
        """Pings Meta API to update local cached health metrics."""
        with SessionLocal() as session:
            repo = MetaAccountRepository(session)
            account = repo.get_by_id(account_id)
            if not account or not account.is_active:
                return None

            phone_info, error = self.cloud_service.get_phone_info(account.phone_number_id, account.access_token)
            if error or not phone_info:
                logger.warning(f"Failed to refresh status for account {account_id}: {error}")
                return self._to_dto(account)

            from datetime import timezone
            updated = repo.update_health_status(
                account_id=account.id,
                api_status=phone_info.api_status,
                quality_rating=phone_info.quality_rating,
                verified_name=phone_info.verified_name,
                display_phone=phone_info.display_phone_number,
                last_synced_at=datetime.now(timezone.utc)
            )
            return self._to_dto(updated) if updated else self._to_dto(account)

    def send_message(self, dto: SendMessageDTO) -> MessageResultDTO:
        with SessionLocal() as session:
            repo = MetaAccountRepository(session)
            account = repo.get_by_id(dto.account_id)
            if not account or not account.is_active:
                return MessageResultDTO(success=False, error="Account not found or inactive.")

            if dto.message_type == "text":
                return self.cloud_service.send_text_message(account.phone_number_id, account.access_token, dto.to, dto.text_body)
            elif dto.message_type == "template":
                return self.cloud_service.send_template_message(
                    account.phone_number_id, 
                    account.access_token, 
                    dto.to, 
                    dto.template_name, 
                    dto.template_language,
                    dto.template_components
                )
            return MessageResultDTO(success=False, error=f"Unknown message type: {dto.message_type}")

    def bulk_send(self, account_id: str, to_phones: List[str], message_type: str, 
                  text_body: str = "", template_name: str = "", template_language: str = "en_US",
                  template_components: Optional[List] = None,
                  progress_callback: Optional[Callable[[int, int, str], None]] = None,
                  completion_callback: Optional[Callable[[int, int], None]] = None):
        """
        Executes a bulk send operation in a background thread with anti-spam compliance delays.
        Progress and completion updates are dispatched via callback to the UI thread.
        """
        import re
        valid_phones = []
        seen = set()
        for phone in to_phones:
            phone_clean = re.sub(r"[^\d+]", "", (phone or "").strip())
            if not phone_clean:
                continue

            digits = phone_clean[1:] if phone_clean.startswith("+") else phone_clean
            if not digits.isdigit() or not (8 <= len(digits) <= 15):
                continue

            normalized = f"+{digits}"
            if normalized not in seen:
                seen.add(normalized)
                valid_phones.append(normalized)
        to_phones = valid_phones

        # 1. Fetch credentials safely using a short-lived session to guarantee thread safety
        with SessionLocal() as session:
            repo = MetaAccountRepository(session)
            account = repo.get_by_id(account_id)
            if not account or not account.is_active:
                if completion_callback: 
                    completion_callback(0, len(to_phones))
                return
                
            phone_id = account.phone_number_id
            token = account.access_token

        def _bulk_worker():
            total = len(to_phones)
            success_count, fail_count = 0, 0
            for index, phone in enumerate(to_phones):
                # 2. Bypass `send_message` and the DB entirely; interact straight with the Cloud API
                if message_type == "text":
                    res = self.cloud_service.send_text_message(phone_id, token, phone, text_body)
                elif message_type == "template":
                    res = self.cloud_service.send_template_message(phone_id, token, phone, template_name, template_language, template_components)
                else:
                    res = MessageResultDTO(success=False, error=f"Unknown type: {message_type}")

                if res.success: success_count += 1
                else: fail_count += 1
                
                if progress_callback: progress_callback(index + 1, total, phone)
                if index < total - 1: time.sleep(random.uniform(1.5, 4.0)) # Anti-spam compliance
            if completion_callback: completion_callback(success_count, fail_count)

        thread = threading.Thread(target=_bulk_worker, daemon=True)
        thread.start()
