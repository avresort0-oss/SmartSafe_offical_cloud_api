from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum

from core.database import Base
from core.models.base import AuditMixin

class InstanceStatus(enum.Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"

class DesktopInstance(AuditMixin, Base):
    """
    Tracks local SmartSafe Desktop apps serving a workspace.
    Used for local fallback and hybrid routing.
    """
    __tablename__ = "desktop_instances"
    
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    instance_id = Column(String(100), unique=True, nullable=False) # HWID or unique client ID
    status = Column(Enum(InstanceStatus), default=InstanceStatus.OFFLINE, nullable=False)
    last_heartbeat = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    # Relationships
    workspace = relationship("Workspace", back_populates="desktop_instances")

    def __repr__(self):
        return f"<DesktopInstance(id='{self.id}', name='{self.name}', status='{self.status.value}')>"
