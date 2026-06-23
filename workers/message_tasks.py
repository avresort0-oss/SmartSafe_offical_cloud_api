import os
import logging
import re
from .celery_app import app
from core.database import SessionLocal
from core.models.message import Message
from integrations.whatsapp_integration import WhatsAppIntegration
from services.message_service import MessageService

logger = logging.getLogger(__name__)

@app.task(bind=True, max_retries=3)
def dispatch_whatsapp_message(self, message_id: str, target_phone: str = ""):
    """Asynchronously dispatches a message via WhatsApp Cloud API."""
    db = SessionLocal()
    message_service = MessageService() # To handle decryption
    try:
        msg = db.query(Message).filter_by(id=message_id).first()
        if not msg:
            logger.error(f"Message {message_id} not found in database.")
            return

        msg.status = "QUEUED"
        db.commit()

        # Decrypt content before sending
        plain_text = message_service._decrypt(msg.content)
        
        # Initialize integration
        wa_integration = WhatsAppIntegration(db)
        
        # Determine target phone from highest-confidence sources first.
        resolved_phone = (target_phone or "").strip()
        if not resolved_phone and msg.contact and msg.contact.phone_e164:
            resolved_phone = msg.contact.phone_e164
        if not resolved_phone and msg.contact_id:
            # Backward-compatible fallback for legacy rows where contact_id stored raw phone.
            if re.fullmatch(r"\+?\d{8,15}", msg.contact_id):
                resolved_phone = msg.contact_id if msg.contact_id.startswith("+") else f"+{msg.contact_id}"
        
        if not resolved_phone:
             # Look for target phone in external_message_id or other fields if needed
             # or handle as error
             msg.status = "FAILED"
             msg.provider_error_code = "MISSING_PHONE"
             db.commit()
             return

        # Dispatch
        try:
            if msg.attachment_path or msg.media_id:
                import mimetypes
                if not msg.media_id and msg.attachment_path and os.path.exists(msg.attachment_path):
                    mime_type, _ = mimetypes.guess_type(msg.attachment_path)
                    mime_type = mime_type or "application/octet-stream"
                    upload_result = wa_integration.upload_media(msg.attachment_path, mime_type)
                    if upload_result.success:
                        msg.media_id = upload_result.message_id
                        if "image" in mime_type: msg.media_type = "image"
                        elif "video" in mime_type: msg.media_type = "video"
                        elif "audio" in mime_type: msg.media_type = "audio"
                        else: msg.media_type = "document"
                        db.commit()
                    else:
                        raise Exception(f"Media upload failed: {upload_result.error}")
                
                if msg.media_id and msg.media_type:
                    result = wa_integration.send_media_message(resolved_phone, msg.media_id, msg.media_type, caption=plain_text)
                else:
                    raise Exception("Missing media_id or media_type after upload attempt.")
            else:
                result = wa_integration.send_message(resolved_phone, plain_text)
            
            if result.success:
                msg.external_message_id = result.message_id
                msg.status = "SENT"
                logger.info(f"Message {message_id} sent successfully. WAMID: {msg.external_message_id}")
            else:
                msg.status = "FAILED"
                msg.provider_error_code = result.error[:64] if result.error else "UNKNOWN_ERROR"
                logger.error(f"Message {message_id} delivery failed: {result.error}")
            
            db.commit()
        except Exception as e:
            # Map specific provider errors if possible
            msg.status = "FAILED"
            msg.provider_error_code = str(e)[:64]
            db.commit()
            raise e

    except Exception as exc:
        db.rollback()
        logger.error(f"Error sending message {message_id}: {exc}")
        # Retry for temporary network issues
        raise self.retry(exc=exc, countdown=60)
    finally:
        db.close()

@app.task
def dispatch_bulk_campaign(campaign_data: dict):
    """Handles a bulk broadcasting campaign by chunking tasks."""
    # Implementation logic for batching would go here
    pass

@app.task(bind=True, max_retries=3)
def download_incoming_media(self, message_id: str):
    db = SessionLocal()
    try:
        msg = db.query(Message).filter_by(id=message_id).first()
        if not msg or not msg.media_id:
            return
            
        wa_integration = WhatsAppIntegration(db)
        creds = wa_integration._get_active_credentials()
        if not creds:
            return
            
        success, file_path = wa_integration.meta_cloud_service.download_media(msg.media_id, creds.access_token)
        if success:
            msg.attachment_path = file_path
            db.commit()
            logger.info(f"Downloaded media for message {message_id} to {file_path}")
        else:
            logger.error(f"Failed to download media for message {message_id}: {file_path}")
            
    except Exception as exc:
        db.rollback()
        logger.error(f"Error downloading media for {message_id}: {exc}")
        raise self.retry(exc=exc, countdown=60)
    finally:
        db.close()

from datetime import datetime, timezone, timedelta
from core.models.bulk_campaign import BulkCampaign

@app.task
def check_sla_breaches():
    db = SessionLocal()
    try:
        ten_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=10)
        
        # Messages received more than 10 mins ago without replies
        unreplied = db.query(Message).filter(
            Message.direction == "INBOUND",
            Message.created_at <= ten_minutes_ago,
            ~Message.replies.any()
        ).all()
        
        for msg in unreplied:
            logger.warning(f"SLA Breach: Message {msg.id} from contact {msg.contact_id} unreplied for >10 mins.")
            # Here we could generate an AuditLog or Alert
            
    except Exception as e:
        logger.error(f"Error checking SLA breaches: {e}")
    finally:
        db.close()

@app.task
def process_scheduled_campaigns():
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        
        campaigns = db.query(BulkCampaign).filter(
            BulkCampaign.status == "PENDING",
            BulkCampaign.scheduled_at <= now
        ).all()
        
        for campaign in campaigns:
            campaign.status = "IN_PROGRESS"
            db.commit()
            logger.info(f"Started campaign {campaign.id}")
            
            # Here we would normally trigger individual dispatch tasks
            # For now, just mark it complete
            campaign.status = "COMPLETED"
            db.commit()
            
    except Exception as e:
        logger.error(f"Error processing campaigns: {e}")
    finally:
        db.close()
