from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from core.database import get_db
from core.models.workspace import Workspace, SyncMode
from api.dependencies import get_current_workspace
from services.integration_service import IntegrationService

router = APIRouter()

class SyncModeUpdate(BaseModel):
    mode: str

class DesktopRegisterRequest(BaseModel):
    name: str
    instance_id: str

@router.patch("/sync-mode")
def update_sync_mode(
    dto: SyncModeUpdate,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    service = IntegrationService(db)
    try:
        updated_ws = service.update_sync_mode(workspace.id, dto.mode)
        return {"workspace_id": updated_ws.id, "new_mode": updated_ws.sync_mode.value}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/desktop/register")
def register_desktop(
    dto: DesktopRegisterRequest,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    service = IntegrationService(db)
    instance = service.register_desktop_instance(workspace.id, dto.name, dto.instance_id)
    return {"status": "registered", "instance_id": instance.instance_id}

@router.get("/desktop/poll")
def poll_messages(
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """Local Desktop apps call this to get messages they need to send."""
    if workspace.sync_mode == SyncMode.CLOUD:
        return []
    
    service = IntegrationService(db)
    messages = service.get_pending_local_messages(workspace.id)
    return [{"id": m.id, "content": m.content, "target_phone": m.contact_id} for m in messages]

@router.post("/desktop/heartbeat/{instance_id}")
def desktop_heartbeat(
    instance_id: str,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    service = IntegrationService(db)
    service.heartbeat(instance_id)
    return {"status": "ok"}
