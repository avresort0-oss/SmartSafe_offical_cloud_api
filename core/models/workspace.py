from sqlalchemy import Column, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import sys
import uuid
import enum

from core.database import Base
from core.models.base import AuditMixin

class WorkspaceRole(enum.Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    MEMBER = "member"
    AGENT = "agent"

class SyncMode(enum.Enum):
    CLOUD = "CLOUD"
    LOCAL = "LOCAL"
    HYBRID = "HYBRID"

class Workspace(AuditMixin, Base):
    __tablename__ = "workspaces"
    name = Column(String(100), nullable=False)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    sync_mode = Column(Enum(SyncMode), default=SyncMode.CLOUD, nullable=False)
    
    # Relationships
    owner = relationship("User", foreign_keys=[owner_id])
    messages = relationship("Message", back_populates="workspace")
    members = relationship("WorkspaceMember", back_populates="workspace")
    desktop_instances = relationship("DesktopInstance", back_populates="workspace")

    def __repr__(self):
        return f"<Workspace(id='{self.id}', name='{self.name}', owner_id='{self.owner_id}')>"

class WorkspaceMember(AuditMixin, Base):
    __tablename__ = "workspace_members"
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    role = Column(Enum(WorkspaceRole), default=WorkspaceRole.MEMBER, nullable=False)
    joined_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    workspace = relationship("Workspace", back_populates="members")
    user = relationship("User", back_populates="workspace_memberships")

    def __repr__(self):
        return f"<WorkspaceMember(id='{self.id}', workspace_id='{self.workspace_id}', user_id='{self.user_id}', role='{self.role.value}')>"