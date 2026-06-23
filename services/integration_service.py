from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import List, Optional
import uuid

from core.models.workspace import Workspace, SyncMode
from core.models.integration import DesktopInstance, InstanceStatus
from core.models.message import Message

class IntegrationService:
    def __init__(self, db: Session):
        self.db = db

    def update_sync_mode(self, workspace_id: str, mode: str) -> Workspace:
        workspace = self.db.query(Workspace).filter(Workspace.id == workspace_id).first()
        if not workspace:
            raise ValueError("Workspace not found")
        
        workspace.sync_mode = SyncMode(mode.upper())
        self.db.commit()
        return workspace

    def register_desktop_instance(self, workspace_id: str, name: str, instance_id: str) -> DesktopInstance:
        instance = self.db.query(DesktopInstance).filter(
            DesktopInstance.workspace_id == workspace_id,
            DesktopInstance.instance_id == instance_id
        ).first()

        if not instance:
            instance = DesktopInstance(
                workspace_id=workspace_id,
                name=name,
                instance_id=instance_id,
                status=InstanceStatus.ONLINE,
                last_heartbeat=datetime.now(timezone.utc)
            )
            self.db.add(instance)
        else:
            instance.name = name
            instance.status = InstanceStatus.ONLINE
            instance.last_heartbeat = datetime.now(timezone.utc)
            instance.is_active = True
        
        self.db.commit()
        return instance

    def heartbeat(self, instance_id: str):
        instance = self.db.query(DesktopInstance).filter(DesktopInstance.instance_id == instance_id).first()
        if instance:
            instance.last_heartbeat = datetime.now(timezone.utc)
            instance.status = InstanceStatus.ONLINE
            self.db.commit()

    def get_pending_local_messages(self, workspace_id: str) -> List[Message]:
        return self.db.query(Message).filter(
            Message.workspace_id == workspace_id,
            Message.status == 'QUEUED_LOCAL'
        ).all()
