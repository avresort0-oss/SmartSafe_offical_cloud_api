import threading
import time
import random
import logging
import sys
import os
import uuid
import hashlib
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))  # Explicitly add project root to sys.path

from core.database import SessionLocal
from core.models.user import User
from core.models.workspace import Workspace
from services.message_service import MessageService, MessageCreateDTO
from services.contact_service import ContactService
from services.conversation_service import ConversationService
from integrations.whatsapp_integration import WhatsAppIntegration

logger = logging.getLogger(__name__)

class MockWAWebhookWorker:
    """
    Daemon thread that simulates incoming HTTP POST webhooks from the Meta WhatsApp Cloud API.
    """
    def __init__(self, whatsapp_integration: WhatsAppIntegration, interval_seconds: int = 25):
        self.running = False
        self.thread = None
        self.interval = interval_seconds
        self.wa_integration = whatsapp_integration

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)

    def _run(self):
        while self.running:
            time.sleep(random.randint(15, 30))
            if not self.running:
                break

            # Simulate receiving a webhook payload from Meta
            mock_payload = {
                "object": "whatsapp_business_account",
                "entry": [{
                    "changes": [{
                        "value": {
                            "messages": [{
                                "from": f"+1555000{random.randint(1000, 9999)}",
                                "type": "text",
                                "text": {"body": random.choice([
                                    "Hi, I need assistance with our enterprise SLA.",
                                    "Can someone review the attached invoice? Thanks.",
                                    "I'm reaching out regarding the new API documentation.",
                                    "Is the support team available for a quick chat?"
                                ])},
                                "id": f"mock-wamid-{uuid.uuid4().hex}"
                            }]
                        }
                    }]
                }]
            }

            db = SessionLocal()
            parsed_msgs = []
            try:
                parsed_msgs = self.wa_integration.parse_webhook(mock_payload)  # Parse outside transaction if it doesn't need DB
                if not parsed_msgs:
                    db.close()  # FIX #2: Prevent session leak when there are no messages to process
                    continue

                ws = db.query(Workspace).first()
                if not ws:
                    logger.warning("[Webhook Simulator] No workspace found to ingest messages into.")
                    db.close()
                    continue

                message_service = MessageService(self.wa_integration)
                contact_service = ContactService(db)
                conversation_service = ConversationService(db)
                for p_msg in parsed_msgs:
                    phone = p_msg["from_phone"]
                    text = p_msg["text"]
                    external_message_id = p_msg.get("wamid") or f"mock-webhook-{uuid.uuid4().hex}"

                    # Auto-provision the external WhatsApp customer in the database
                    customer = db.query(User).filter_by(username=phone).first()
                    if not customer:
                        # FIX #1 SECURITY: Use a deterministic but cryptographically irreversible hash.
                        # These are external-only WA accounts and must never be able to log in via the app.
                        _disabled_hash = hashlib.sha256(f"DISABLED_WA_ONLY:{phone}".encode()).hexdigest()
                        customer = User(username=phone, email=f"{phone}@wa.external", password_hash=_disabled_hash, is_active=True)
                        db.add(customer)
                        db.flush()  # Flush to get customer.id before commit
                        logger.info(f"[Webhook Simulator] Auto-provisioned new WhatsApp user: {phone}")

                    contact = contact_service.upsert_whatsapp_contact(
                        workspace_id=ws.id,
                        phone=phone,
                        display_name=customer.username,
                        email=customer.email,
                    )
                    conversation = conversation_service.get_or_create_conversation(
                        workspace_id=ws.id,
                        contact_id=contact.id,
                        meta_account_id=None,
                    )
                    dto = MessageCreateDTO(
                        content=text,
                        sender_id=customer.id,
                        workspace_id=ws.id,
                        conversation_id=conversation.id,
                        contact_id=contact.id,
                        direction="INBOUND",
                        channel="WHATSAPP",
                        external_message_id=external_message_id,
                    )
                    message_service.send_message(dto)  # This internally commits the message
                    conversation_service.update_on_new_message(
                        conversation_id=conversation.id,
                        preview=text,
                        message_ts=datetime.now(timezone.utc),
                        inbound=True,
                    )
                    logger.info(f"[Webhook Simulator] Ingested incoming WhatsApp message from {phone}")
                db.commit()  # Commit all changes from this cycle
            except Exception as e:
                logger.error(f"[Webhook Simulator] Error processing webhook: {e}", exc_info=True)
                db.rollback()
            finally:
                db.close()
