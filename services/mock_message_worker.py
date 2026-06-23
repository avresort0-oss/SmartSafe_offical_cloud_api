import threading
import time
import logging
import random
import uuid
import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.database import SessionLocal
from core.models.user import User
from core.models.workspace import Workspace

logger = logging.getLogger(__name__)

MOCK_SENDERS = [
    ("Customer_Alice", "alice@mock.wa"),
    ("Customer_Bob", "bob@mock.wa"),
    ("Customer_Carlos", "carlos@mock.wa"),
    ("Customer_Diana", "diana@mock.wa"),
]

MOCK_MESSAGES = [
    "Hi, I need help with my order.",
    "When will my package arrive?",
    "Can you check on my account?",
    "I'd like to update my contact info.",
    "Is there a discount available?",
    "Thanks for your help!",
    "Please call me back when available.",
    "I have a question about billing.",
]


class MockMessageWorker:
    """
    Daemon thread worker that periodically simulates incoming WhatsApp messages.
    Used in mock/demo mode to populate the chat with realistic test data.
    """

    def __init__(self, interval_seconds: int = 30):
        self.running = False
        self.thread = None
        self.interval = interval_seconds
        self._stop_event = threading.Event()

    def start(self):
        if not self.running:
            self.running = True
            self._stop_event.clear()
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()
            logger.info("[MockMessageWorker] Started — simulating incoming WA messages.")

    def stop(self):
        self.running = False
        self._stop_event.set()
        if self.thread:
            self.thread.join(timeout=2.0)
        logger.info("[MockMessageWorker] Stopped.")

    def _run(self):
        while self.running:
            self._stop_event.wait(self.interval)
            if not self.running:
                break
            try:
                self._inject_mock_message()
            except Exception as e:
                logger.error(f"[MockMessageWorker] Error injecting mock message: {e}", exc_info=True)

    def _inject_mock_message(self):
        db = SessionLocal()
        try:
            workspaces = db.query(Workspace).all()
            if not workspaces:
                logger.debug("[MockMessageWorker] No workspaces found, skipping mock injection.")
                return
            workspace = random.choice(workspaces)

            sender_name, sender_email = random.choice(MOCK_SENDERS)
            message_text = random.choice(MOCK_MESSAGES)

            # Auto-provision mock customer user if not exists
            customer = db.query(User).filter_by(email=sender_email).first()
            if not customer:
                customer = User(
                    username=sender_name,
                    email=sender_email,
                    password_hash="mock_wa_user",
                    is_active=True,
                )
                db.add(customer)
                db.flush()

            # Import here to avoid circular imports at module level
            from services.message_service import MessageService, MessageCreateDTO
            from services.contact_service import ContactService
            from services.conversation_service import ConversationService
            from services.settings_service import SettingsService
            from integrations.whatsapp_integration import WhatsAppIntegration

            settings_service = SettingsService(db)
            wa_integration = WhatsAppIntegration(db)
            message_service = MessageService(wa_integration)
            contact_service = ContactService(db)
            conversation_service = ConversationService(db)

            normalized_phone = f"+1{abs(hash(sender_email)) % 9000000000 + 1000000000}"
            contact = contact_service.upsert_whatsapp_contact(
                workspace_id=workspace.id,
                phone=normalized_phone,
                display_name=sender_name,
                email=sender_email,
            )
            conversation = conversation_service.get_or_create_conversation(
                workspace_id=workspace.id,
                contact_id=contact.id,
                meta_account_id=None,
            )

            dto = MessageCreateDTO(
                content=message_text,
                sender_id=customer.id,
                workspace_id=workspace.id,
                conversation_id=conversation.id,
                contact_id=contact.id,
                direction="INBOUND",
                channel="WHATSAPP",
                external_message_id=f"mock-{uuid.uuid4().hex}",
            )
            message_service.send_message(dto)
            conversation_service.update_on_new_message(
                conversation_id=conversation.id,
                preview=message_text,
                message_ts=datetime.now(timezone.utc),
                inbound=True,
            )
            db.commit()
            logger.info(f"[MockMessageWorker] Injected mock message from '{sender_name}': {message_text}")
        except Exception as e:
            db.rollback()
            logger.error(f"[MockMessageWorker] DB error: {e}", exc_info=True)
        finally:
            db.close()
