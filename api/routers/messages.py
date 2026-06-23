from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, File, UploadFile, Form
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
import os
import logging

from core.database import get_db
from sqlalchemy.orm import Session
from services.message_service import MessageService, MessageCreateDTO, MessageResponseDTO
from workers.message_tasks import dispatch_whatsapp_message
from api.dependencies import get_current_workspace
from core.models.workspace import Workspace, SyncMode
from utils.audit_utils import audit_log

logger = logging.getLogger(__name__)

# Router setup
router = APIRouter()

# --- Pydantic Data Models ---
class MessageSendRequest(BaseModel):
    target_phone: str
    content: str
    sender_id: str
    contact_id: str
    meta_account_id: Optional[str] = None
    template_name: Optional[str] = None
    template_language: Optional[str] = "en_US"
    media_url: Optional[str] = None
    route_to_whatsapp: bool = False

class BulkMessageRequest(BaseModel):
    recipients: List[str]
    content: str
    sender_id: str
    template_name: Optional[str] = None
    meta_account_id: Optional[str] = None

class MessageStatusResponse(BaseModel):
    message_id: str
    status: str
    external_id: Optional[str] = None
    error_code: Optional[str] = None

from core.database import SessionLocal
from core.models.message import Message

@router.post("/send", response_model=MessageResponseDTO, status_code=202)
def send_message(
    dto: MessageSendRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """
    Sends a single message via WhatsApp Cloud API.
    Enforces strict tenant isolation via X-API-Key.
    """
    try:
        message_service = MessageService()
        
        # 2. Check Sync Mode for Hybrid Routing
        status = "PENDING"
        if workspace.sync_mode == SyncMode.LOCAL:
            status = "QUEUED_LOCAL"
            logger.info(f"Message {dto.contact_id} diverted to LOCAL queue for workspace {workspace.id}")

        # 3. Map to Internal DTO with authenticated workspace_id
        create_dto = MessageCreateDTO(
            content=dto.content,
            sender_id=dto.sender_id,
            workspace_id=workspace.id, 
            contact_id=dto.contact_id,
            direction="OUTBOUND",
            channel="CLOUD" if dto.route_to_whatsapp else "LOCAL",
            route_to_whatsapp=dto.route_to_whatsapp, 
            status=status
        )

        # 4. Persist Encrypted Message
        saved_msg = message_service.send_message(create_dto)
        
        # 5. Enqueue for Background Processing (Only if CLOUD/HYBRID)
        if dto.route_to_whatsapp:
            try:
                dispatch_whatsapp_message.delay(saved_msg.id, dto.target_phone)
            except Exception as enqueue_error:
                logger.error(f"Celery enqueue failed for message {saved_msg.id}: {enqueue_error}")
                # Keep API request successful; mark message for later retry by background sync.
                message_service.update_message_status(saved_msg.id, "QUEUED")
        
        # 6. Log Audit Event
        audit_log(
            background_tasks, db, workspace.id, 
            action="SEND_MESSAGE", resource_type="MESSAGE", resource_id=saved_msg.id,
            metadata={"target_phone": dto.target_phone, "mode": workspace.sync_mode.value}
        )

        return saved_msg
    except Exception as e:
        logger.error(f"Error in send_message endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/send/media", response_model=MessageResponseDTO, status_code=202)
def send_media_message(
    background_tasks: BackgroundTasks,
    target_phone: str = Form(...),
    content: str = Form(default=""),
    sender_id: str = Form(...),
    contact_id: str = Form(...),
    route_to_whatsapp: bool = Form(False),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    try:
        message_service = MessageService()
        
        status = "PENDING"
        if workspace.sync_mode == SyncMode.LOCAL:
            status = "QUEUED_LOCAL"
            logger.info(f"Message {contact_id} diverted to LOCAL queue for workspace {workspace.id}")

        # Save file temporarily
        attachments_dir = os.path.join(os.getcwd(), "attachments")
        os.makedirs(attachments_dir, exist_ok=True)
        safe_filename = f"{uuid.uuid4().hex[:8]}_{file.filename}"
        target_path = os.path.join(attachments_dir, safe_filename)
        
        with open(target_path, "wb") as buffer:
            import shutil
            shutil.copyfileobj(file.file, buffer)

        create_dto = MessageCreateDTO(
            content=content,
            sender_id=sender_id,
            workspace_id=workspace.id, 
            contact_id=contact_id,
            direction="OUTBOUND",
            channel="CLOUD" if route_to_whatsapp else "LOCAL",
            route_to_whatsapp=route_to_whatsapp, 
            status=status,
            attachment_path=target_path
        )

        saved_msg = message_service.send_message(create_dto)
        
        if route_to_whatsapp:
            try:
                dispatch_whatsapp_message.delay(saved_msg.id, target_phone)
            except Exception as enqueue_error:
                logger.error(f"Celery enqueue failed for media message {saved_msg.id}: {enqueue_error}")
                message_service.update_message_status(saved_msg.id, "QUEUED")
        
        audit_log(
            background_tasks, db, workspace.id, 
            action="SEND_MEDIA_MESSAGE", resource_type="MESSAGE", resource_id=saved_msg.id,
            metadata={"target_phone": target_phone, "mode": workspace.sync_mode.value, "filename": file.filename}
        )

        return saved_msg
    except Exception as e:
        logger.error(f"Error in send_media_message endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/bulk", status_code=202)
def send_bulk_messages(
    dto: BulkMessageRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """
    Triggers a bulk broadcasting campaign.
    """
    try:
        message_service = MessageService()
        job_id = str(uuid.uuid4())
        
        for recipient in dto.recipients:
            # Create record for each recipient
            create_dto = MessageCreateDTO(
                content=dto.content, # Use provided body text for bulk text campaigns
                sender_id=dto.sender_id,
                workspace_id=workspace.id,
                contact_id=recipient,
                direction="OUTBOUND",
                channel="CLOUD",
                status="PENDING"
            )
            saved_msg = message_service.send_message(create_dto)
            try:
                dispatch_whatsapp_message.delay(saved_msg.id, recipient)
            except Exception as enqueue_error:
                logger.error(f"Celery enqueue failed for bulk message {saved_msg.id}: {enqueue_error}")
                message_service.update_message_status(saved_msg.id, "QUEUED")

        # Log Audit Event
        audit_log(
            background_tasks, db, workspace.id, 
            action="BULK_SEND", resource_type="CAMPAIGN", resource_id=job_id,
            metadata={"count": len(dto.recipients), "template": dto.template_name}
        )

        return {"job_id": job_id, "status": "queued", "count": len(dto.recipients)}
    except Exception as e:
        logger.error(f"Error in bulk_send endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{message_id}/status", response_model=MessageStatusResponse)
def get_message_status(message_id: str, db: Session = Depends(get_db)):
    try:
        msg = db.query(Message).filter_by(id=message_id).first()
        if not msg:
            raise HTTPException(status_code=404, detail="Message not found")
        
        return {
            "message_id": msg.id,
            "status": msg.status,
            "external_id": msg.external_message_id,
            "error_code": msg.provider_error_code
        }
    except Exception as e:
        logger.error(f"Error fetching status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
