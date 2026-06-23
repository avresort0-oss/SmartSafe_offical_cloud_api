import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from core.database import Base
from core.models.base import AuditMixin

class AuditLog(AuditMixin, Base):
    """
    Captures sensitive system actions for compliance and enterprise auditing.
    """
    __tablename__ = "audit_logs"
    
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String(64), nullable=False, index=True) # e.g. "SEND_MESSAGE", "DELETE_CONTACT"
    resource_type = Column(String(32), nullable=False, index=True) # e.g. "MESSAGE", "CONTACT"
    resource_id = Column(String(36), nullable=True, index=True)
    metadata_json = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)

    # Relationships
    workspace = relationship("Workspace")
    user = relationship("User")

    def __repr__(self):
        return f"<AuditLog(id='{self.id}', action='{self.action}', resource_type='{self.resource_type}')>"
