import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship, Mapped, mapped_column
from core.database import Base
from core.models.base import AuditMixin

class ApiKey(AuditMixin, Base):
    """
    Stores scoped API keys for workspace-level authentication.
    The actual key is never stored in plain text; only the argon2 hash is persisted.
    """
    __tablename__ = "api_keys"
    
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    label = Column(String(100), nullable=False) # e.g. "Production Server", "Zapier Integration"
    key_hash = Column(String(255), nullable=False, unique=True)
    prefix = Column(String(8), nullable=False) # e.g. "sk_live_"
    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    workspace = relationship("Workspace")

    def __repr__(self):
        return f"<ApiKey(id='{self.id}', label='{self.label}', workspace_id='{self.workspace_id}')>"
