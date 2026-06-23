from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from core.database import get_db
from api.dependencies import get_current_workspace
from services.template_service import TemplateService

router = APIRouter()

@router.post("/sync")
async def sync_templates(
    meta_account_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    workspace = Depends(get_current_workspace)
):
    """Triggers an asynchronous sync of message templates from Meta."""
    service = TemplateService(db)
    
    # We run it in background to avoid blocking the API
    background_tasks.add_task(service.sync_templates, workspace.id, meta_account_id)
    
    return {"message": "Template synchronization started", "workspace_id": workspace.id}

@router.get("/")
async def list_templates(
    meta_account_id: str = None,
    db: Session = Depends(get_db),
    workspace = Depends(get_current_workspace)
):
    """Lists all cached templates for the workspace."""
    service = TemplateService(db)
    templates = service.get_templates(workspace.id, meta_account_id)
    return templates
