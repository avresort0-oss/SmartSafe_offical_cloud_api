from fastapi import APIRouter, Depends, Request, Response, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
import os
import logging

from core.database import get_db
from core.models.message import Message
from core.models.contact import Contact
from integrations.whatsapp_integration import WhatsAppIntegration
from services.message_service import MessageService

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/")
def verify_webhook(request: Request):
    """Webhook verification for Meta Cloud API."""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    # Uses environment variable for verification token
    verify_token = os.getenv("WEBHOOK_VERIFY_TOKEN", "smartsafe_secret")

    if mode and token:
        if mode == "subscribe" and token == verify_token:
            logger.info("Webhook verified successfully.")
            return Response(content=challenge, media_type="text/plain")
        else:
            raise HTTPException(status_code=403, detail="Verification failed")
    
    raise HTTPException(status_code=400, detail="Missing parameters")

@router.post("/")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Receives webhook events from Meta Cloud API."""
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    wa_integration = WhatsAppIntegration(db)
    message_service = MessageService()
    parsed_events = wa_integration.parse_webhook(payload)

    for event in parsed_events:
        event_type = event.get("type")
        wamid = event.get("wamid")
        
        if event_type == "status":
            # Update delivery status
            status = event.get("status") # sent, delivered, read, failed
            if wamid and status:
                msg = db.query(Message).filter(Message.external_message_id == wamid).first()
                if msg:
                    msg.status = status.upper()
                    db.commit()
                    logger.info(f"Updated message {msg.id} status to {status.upper()}")
                    
        elif event_type in ["text", "image", "video", "document", "audio"]:
            # Process incoming message
            from_phone = event.get("from_phone")
            text = event.get("text", "")
            media_id = event.get("media_id")
            
            # Find contact by phone
            search_phone = f"+{from_phone.lstrip('+')}"
            contact = db.query(Contact).filter(Contact.phone_e164 == search_phone).first()
            
            if not contact:
                logger.warning(f"Received message from unknown contact: {search_phone}")
                # Optional: create a new contact automatically here
                continue
                
            # Check if message already exists
            existing = db.query(Message).filter(Message.external_message_id == wamid).first()
            if existing:
                continue
                
            # Create incoming message
            new_msg = Message(
                workspace_id=contact.workspace_id,
                contact_id=contact.id,
                content=message_service._encrypt(text),
                direction="INBOUND",
                channel="CLOUD",
                status="DELIVERED",
                external_message_id=wamid,
                media_id=media_id,
                media_type=event_type if event_type != "text" else None
            )
            db.add(new_msg)
            db.commit()
            logger.info(f"Saved incoming message from {search_phone}")
            
            # If media is present, we should trigger a celery task to download it
            if media_id:
                try:
                    from workers.message_tasks import download_incoming_media
                    download_incoming_media.delay(new_msg.id)
                except ImportError:
                    pass

    return {"status": "ok"}
