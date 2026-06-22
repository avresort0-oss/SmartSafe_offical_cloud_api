import sys
import os
import threading
import logging
import json
import uuid
import hmac
import hashlib
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import bcrypt

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.database import SessionLocal
from core.models.user import User
from core.models.workspace import Workspace
from core.models.message import Message
from services.message_service import MessageService, MessageCreateDTO
from services.contact_service import ContactService
from services.conversation_service import ConversationService
from services.settings_service import SettingsService
from integrations.whatsapp_integration import WhatsAppIntegration
from services.auto_reply_service import AutoReplyService
from utils.audit_utils import log_audit_event

logger = logging.getLogger(__name__)

# Global references for the HTTP handler since it's instantiated per-request by the server
_wa_integration = None
_verify_token = "" # Meta Webhook Verify Token

class WebhookHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handles Meta's Webhook Verification requests."""
        parsed_path = urlparse(self.path)
        query_params = parse_qs(parsed_path.query)
        
        if 'hub.mode' in query_params and 'hub.verify_token' in query_params:
            mode = query_params['hub.mode'][0]
            token = query_params['hub.verify_token'][0]
            
            if mode == 'subscribe' and token == _verify_token:
                challenge = query_params.get('hub.challenge', [''])[0]
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(challenge.encode('utf-8'))
                logger.info("[Webhook Receiver] Meta Webhook verified successfully.")
                return
            else:                self.send_response(403)
                self.end_headers()
                return
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        """Handles incoming WhatsApp messages pushed by Meta."""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        # 1. Signature Validation
        signature_header = self.headers.get('X-Hub-Signature-256', '')
        if signature_header:
            app_secret = os.getenv("META_APP_SECRET", "")
            if app_secret:
                expected_hash = hmac.new(app_secret.encode('utf-8'), post_data, hashlib.sha256).hexdigest()
                if not hmac.compare_digest(f"sha256={expected_hash}", signature_header):
                    logger.warning("[Webhook Receiver] Invalid signature. Rejecting payload.")
                    self.send_response(403)
                    self.end_headers()
                    return
            else:
                logger.warning("[Webhook Receiver] META_APP_SECRET not set; bypassing signature validation.")
        
        try:
            payload = json.loads(post_data.decode('utf-8'))
            self._process_payload(payload, post_data)
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"EVENT_RECEIVED")
        except Exception as e:
            logger.error(f"[Webhook Receiver] Error processing webhook: {e}")
            # Global error alert (no workspace yet)
            db = SessionLocal()
            try:
                log_audit_event(db, workspace_id="SYSTEM", action="WEBHOOK_CRITICAL_ERROR", resource_type="WEBHOOK", metadata={"error": str(e)})
            finally:
                db.close()
            self.send_response(500)
            self.end_headers()
            
    def _process_payload(self, payload, raw_bytes=b""):
        if not _wa_integration:
            return
            
        db = SessionLocal()
        new_event = None
        payload_hash = hashlib.sha256(raw_bytes).hexdigest() if raw_bytes else None

        try:
            from core.models.webhook_event import WebhookEvent
            if payload_hash:
                existing_event = db.query(WebhookEvent).filter_by(payload_hash=payload_hash).first()
                if existing_event:
                    logger.info(f"[Webhook Receiver] Idempotent hit: Event {payload_hash} already processed.")
                    return
                
                # Create PENDING event
                new_event = WebhookEvent(
                    payload_hash=payload_hash,
                    raw_payload=raw_bytes.decode('utf-8') if raw_bytes else "",
                    status="PENDING"
                )
                db.add(new_event)
                db.commit() # Commit quickly to claim the event
            
            parsed_msgs = _wa_integration.parse_webhook(payload)
            if not parsed_msgs:
                if new_event:
                    new_event.status = "PROCESSED"
                    db.commit()
                return
                
            settings_service = SettingsService(db)
            message_service = MessageService(_wa_integration)
            contact_service = ContactService(db)
            conversation_service = ConversationService(db)
            from core.models.meta_account import MetaAccount
            auto_reply_service = AutoReplyService()

            for p_msg in parsed_msgs:
                phone_number_id = p_msg.get("phone_number_id")

                # Explicit Routing Logic (needed for both status events and inbound messages)
                account = db.query(MetaAccount).filter_by(phone_number_id=phone_number_id).first() if phone_number_id else None
                if not account:
                    logger.warning(f"[Webhook Receiver] Unroutable event. No matching MetaAccount for phone_number_id {phone_number_id}.")
                    continue

                ws = db.query(Workspace).filter_by(id=account.workspace_id).first()
                if not ws:
                    logger.warning(f"[Webhook Receiver] Found account but no workspace for phone_number_id {phone_number_id}.")
                    continue

                # Check for status event
                if p_msg.get("type") == "status":
                    external_message_id = p_msg.get("wamid")
                    status_val = p_msg.get("status")
                    if external_message_id:
                        msg_record = db.query(Message).filter_by(external_message_id=external_message_id).first()
                        if msg_record:
                            msg_record.status = status_val.upper()
                            logger.info(f"Updated message {external_message_id} to state: {status_val.upper()}")

                            # Audit status update
                            log_audit_event(
                                db, ws.id,
                                action="META_STATUS_UPDATE",
                                resource_type="MESSAGE",
                                resource_id=msg_record.id,
                                metadata={"status": status_val, "wamid": external_message_id}
                            )
                    continue

                phone = p_msg.get("from_phone")
                text = p_msg.get("text")
                msg_type = p_msg.get("type", "text")
                external_message_id = p_msg.get("wamid")

                if external_message_id:
                    existing = db.query(Message).filter(
                        Message.external_message_id == external_message_id,
                        Message.channel == "WHATSAPP",
                    ).first()
                    if existing:
                        logger.info(f"[Webhook Receiver] Duplicate webhook message ignored: {external_message_id}")
                        continue
                
                # Auto-provision the external WhatsApp customer
                customer = db.query(User).filter_by(username=phone).first()
                if not customer:
                    disabled_secret = f"DISABLED_WA_ONLY:{phone}:{uuid.uuid4().hex}"
                    disabled_hash = bcrypt.hashpw(disabled_secret.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
                    customer = User(
                        username=phone,
                        email=f"{phone}@wa.external",
                        password_hash=disabled_hash,
                        is_active=False,
                    )
                    db.add(customer)
                    db.flush()

                contact = contact_service.upsert_whatsapp_contact(
                    workspace_id=ws.id,
                    phone=phone,
                    display_name=customer.username,
                    email=customer.email,
                )
                conversation = conversation_service.get_or_create_conversation(
                    workspace_id=ws.id,
                    contact_id=contact.id,
                    meta_account_id=account.id,
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
                    attachment_path=p_msg.get("media_id")
                )
                message_service.send_message(dto)
                
                # Premium Auto Reply Bot Logic
                bot_response = auto_reply_service.process_incoming_message(ws.id, text)
                if bot_response:
                    reply_text = bot_response["content"]
                    reply_attachment = bot_response.get("attachment_path")
                    
                    # Send response back via WhatsApp
                    reply_dto = MessageCreateDTO(
                        content=reply_text,
                        sender_id="system_bot", # Or a dedicated bot user id
                        workspace_id=ws.id,
                        conversation_id=conversation.id,
                        contact_id=contact.id,
                        direction="OUTBOUND",
                        channel="WHATSAPP",
                        route_to_whatsapp=True,
                        target_phone=phone,
                        attachment_path=reply_attachment
                    )
                    message_service.send_message(reply_dto)
                    logger.info(f"[AutoReply] Sent automated response to {phone}")

                conversation_service.update_on_new_message(
                    conversation_id=conversation.id,
                    preview=text,
                    message_ts=datetime.now(timezone.utc),
                    inbound=True,
                )
                logger.info(f"[Webhook Receiver] Ingested live message from {phone}")
            
            if new_event:
                new_event.status = "PROCESSED"
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"[Webhook Receiver] Failed to ingest message: {e}")
            
            # Audit Ingestion Failure
            try:
                # Try to get workspace_id if available in context
                current_ws_id = ws.id if 'ws' in locals() and ws else "UNKNOWN"
                log_audit_event(
                    db, current_ws_id, 
                    action="META_WEBHOOK_ERROR", 
                    resource_type="WEBHOOK", 
                    metadata={"error": str(e), "payload_summary": str(payload)[:500]}
                )
            except Exception as audit_exc:
                logger.error(f"[Webhook Receiver] Failed to record ingestion-failure audit event: {audit_exc}")

            if new_event:
                try:
                    new_event.status = "FAILED"
                    new_event.error_message = str(e)
                    db.commit()
                except Exception as inner_e:
                    logger.error(f"Failed to update DLQ state: {inner_e}")
        finally:
            db.close()
            
    def log_message(self, format, *args):
        """Overrides default HTTP logging to prevent console spam."""
        pass

class WebhookReceiverWorker:
    """Daemon thread that runs the embedded HTTP server for Meta webhooks."""
    def __init__(self, whatsapp_integration: WhatsAppIntegration, port: int = 8080, verify_token: str = ""):
        global _wa_integration, _verify_token
        _wa_integration = whatsapp_integration
        _verify_token = verify_token
        self.port = port
        self.server = None
        self.thread = None

    def start(self):
        if not self.server:
            self.server = HTTPServer(('', self.port), WebhookHandler)
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            logger.info(f"Real Webhook Receiver started on port {self.port}.")

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
            if self.thread:
                self.thread.join(timeout=2.0)
            logger.info("Webhook Receiver stopped.")
