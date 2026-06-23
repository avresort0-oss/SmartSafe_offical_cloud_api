import os
import sys
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)
import shutil
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import List, Optional
import logging
from cryptography.fernet import Fernet, InvalidToken

from core.database import SessionLocal
from integrations.whatsapp_integration import WhatsAppIntegration
from core.repositories.message_repository import MessageRepository
from services.settings_service import SettingsService
from core.models.message import Message


# --- DTOs API Boundaries ---

logger = logging.getLogger(__name__)

@dataclass
class MessageCreateDTO:
    content: str
    sender_id: str
    workspace_id: str
    conversation_id: Optional[str] = None
    contact_id: Optional[str] = None
    parent_id: Optional[str] = None
    direction: str = "OUTBOUND"
    channel: str = "LOCAL"
    external_message_id: Optional[str] = None
    route_to_whatsapp: bool = False
    target_phone: Optional[str] = None
    attachment_path: Optional[str] = None
    status: str = "PENDING"
    provider_error_code: Optional[str] = None


@dataclass
class MessageResponseDTO:
    id: str
    content: str
    sender_id: str
    sender_name: str
    workspace_id: str
    conversation_id: Optional[str]
    contact_id: Optional[str]
    direction: str
    channel: str
    external_message_id: Optional[str]
    timestamp: str
    created_at: str
    updated_at: str
    is_synced: bool = False
    parent_id: Optional[str] = None
    attachment_path: Optional[str] = None
    is_starred: bool = False
    status: str = "PENDING"
    provider_error_code: Optional[str] = None


# --- Business Logic Service ---

class MessageService:
    def __init__(self, whatsapp_integration: Optional[WhatsAppIntegration] = None):
        self.whatsapp_integration = whatsapp_integration
        self._initialize_encryption()

    def _initialize_encryption(self):
        with SessionLocal() as session:
            settings_service = SettingsService(session)
            e2ee_key_env = os.getenv("E2EE_MASTER_KEY")
            if not e2ee_key_env:
                e2ee_key_env = settings_service.get_setting("E2EE_MASTER_KEY")

            if e2ee_key_env:
                e2ee_key_env = e2ee_key_env.strip().strip('"').strip("'")

            if not e2ee_key_env:
                e2ee_key_env = Fernet.generate_key().decode('utf-8')
                settings_service.set_setting("E2EE_MASTER_KEY", e2ee_key_env)
                logger.info("Auto-provisioned a persistent E2EE_MASTER_KEY in App Settings.")

            try:
                self.cipher_suite = Fernet(e2ee_key_env.encode('utf-8'))
            except (ValueError, InvalidToken) as e:
                logger.warning(f"Existing encryption key is invalid or corrupted. Generating a new one. Error: {e}")
                new_key = Fernet.generate_key().decode('utf-8')
                settings_service.set_setting("E2EE_MASTER_KEY", new_key)
                self.cipher_suite = Fernet(new_key.encode('utf-8'))

    def _encrypt(self, plain_text: str) -> str:
        if not plain_text:
            plain_text = ""
        return self.cipher_suite.encrypt(plain_text.encode('utf-8')).decode('utf-8')

    def _decrypt(self, cipher_text: str) -> str:
        try:
            return self.cipher_suite.decrypt(cipher_text.encode('utf-8')).decode('utf-8')
        except InvalidToken:
            return cipher_text

    def _to_response(self, msg: Message, content_override: Optional[str] = None, sender_name_override: Optional[str] = None) -> MessageResponseDTO:
        return MessageResponseDTO(
            id=msg.id,
            content=content_override if content_override is not None else self._decrypt(msg.content),
            sender_id=msg.sender_id,
            sender_name=sender_name_override if sender_name_override is not None else (msg.sender.username if msg.sender else "Unknown"),
            workspace_id=msg.workspace_id,
            conversation_id=msg.conversation_id,
            contact_id=msg.contact_id,
            direction=msg.direction or "OUTBOUND",
            channel=msg.channel or "LOCAL",
            external_message_id=msg.external_message_id,
            timestamp=msg.created_at.strftime("%I:%M %p") if msg.created_at else "Now",
            created_at=msg.created_at.isoformat() if msg.created_at else datetime(1970, 1, 1, tzinfo=timezone.utc).isoformat(),
            updated_at=msg.updated_at.isoformat() if msg.updated_at else datetime(1970, 1, 1, tzinfo=timezone.utc).isoformat(),
            is_synced=msg.is_synced,
            parent_id=msg.parent_id,
            attachment_path=msg.attachment_path,
            is_starred=msg.is_starred,
            status=msg.status or "PENDING",
            provider_error_code=msg.provider_error_code,
        )

    def send_message(self, dto: MessageCreateDTO) -> MessageResponseDTO:
        target_path = None
        if dto.attachment_path and os.path.exists(dto.attachment_path):
            attachments_dir = os.path.join(os.getcwd(), "attachments")
            os.makedirs(attachments_dir, exist_ok=True)
            safe_filename = f"{uuid.uuid4().hex[:8]}_{os.path.basename(dto.attachment_path)}"
            target_path = os.path.join(attachments_dir, safe_filename)
            shutil.copy2(dto.attachment_path, target_path)

        with SessionLocal() as session:
            repo = MessageRepository(session)
            if dto.external_message_id:
                existing_msg = session.query(Message).filter_by(external_message_id=dto.external_message_id).first()
                if existing_msg:
                    return self._to_response(existing_msg, content_override=dto.content)

            encrypted_content = self._encrypt(dto.content)
            msg = Message(
                content=encrypted_content,
                sender_id=dto.sender_id,
                workspace_id=dto.workspace_id,
                conversation_id=dto.conversation_id,
                contact_id=dto.contact_id,
                parent_id=dto.parent_id,
                direction=dto.direction,
                channel=dto.channel,
                external_message_id=dto.external_message_id,
                attachment_path=target_path,
                status=dto.status or "PENDING",
                provider_error_code=dto.provider_error_code,
            )
            saved_msg = repo.add(msg)
        
        if dto.route_to_whatsapp and self.whatsapp_integration and dto.target_phone:
            import threading
            def _dispatch():
                try:
                    self.whatsapp_integration.send_message(dto.target_phone, dto.content)
                except Exception as e:
                    logger.error("Failed to send WhatsApp message: %s", e)
            threading.Thread(target=_dispatch, daemon=True).start()
        
        return self._to_response(saved_msg, content_override=dto.content, sender_name_override="Current User")

    def get_recent_messages(self, workspace_id: str, since_timestamp: Optional[str] = None, conversation_id: Optional[str] = None) -> List[MessageResponseDTO]:
        parsed_since = None
        if since_timestamp:
            try:
                parsed_since = datetime.fromisoformat(since_timestamp.replace("Z", "+00:00"))
            except ValueError:
                pass

        with SessionLocal() as session:
            repo = MessageRepository(session)
            msgs = repo.get_recent_messages(workspace_id, since_timestamp=parsed_since, conversation_id=conversation_id)
            return [self._to_response(m) for m in msgs]

    def search_messages(self, query: str) -> List[MessageResponseDTO]:
        with SessionLocal() as session:
            repo = MessageRepository(session)
            msgs = repo.get_all_active_messages(limit=500)
            results = []
            query_lower = query.lower()
            for m in msgs:
                plain_text = self._decrypt(m.content)
                if query_lower in plain_text.lower():
                    results.append(self._to_response(m, content_override=plain_text))
            return results

    def delete_message(self, message_id: str) -> bool:
        with SessionLocal() as session:
            repo = MessageRepository(session)
            return repo.soft_delete(message_id)

    def toggle_message_star(self, message_id: str) -> bool:
        with SessionLocal() as session:
            repo = MessageRepository(session)
            return repo.toggle_star(message_id)

    def update_message_status(self, message_id: str, status: str, provider_error_code: Optional[str] = None) -> bool:
        with SessionLocal() as session:
            msg = session.query(Message).filter_by(id=message_id).first()
            if msg:
                msg.status = status
                if provider_error_code:
                    msg.provider_error_code = provider_error_code
                session.commit()
                return True
            return False
