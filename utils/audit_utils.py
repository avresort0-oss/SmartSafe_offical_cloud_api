import logging
from sqlalchemy.orm import Session
from fastapi import BackgroundTasks
from typing import Optional, Any
from core.models.audit_log import AuditLog

logger = logging.getLogger(__name__)

def log_audit_event(
    db: Session,
    workspace_id: str,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    user_id: Optional[str] = None,
    metadata: Optional[dict] = None,
    ip_address: Optional[str] = None
):
    """
    Synchronous helper to persist an audit log entry.
    Usually called via BackgroundTasks to avoid blocking the main request.
    """
    try:
        log = AuditLog(
            workspace_id=workspace_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata_json=metadata,
            ip_address=ip_address
        )
        db.add(log)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to write audit log: {e}")

def audit_log(
    background_tasks: BackgroundTasks,
    db: Session,
    workspace_id: str,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    user_id: Optional[str] = None,
    metadata: Optional[dict] = None
):
    """
    Queues an audit log entry to be written in the background.
    """
    background_tasks.add_task(
        log_audit_event,
        db=db,
        workspace_id=workspace_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=user_id,
        metadata=metadata
    )
