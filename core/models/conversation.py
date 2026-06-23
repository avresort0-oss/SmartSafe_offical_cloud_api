import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from core.database import Base
from core.models.base import AuditMixin


class Conversation(AuditMixin, Base):
    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint("workspace_id", "contact_id", "meta_account_id", name="uq_conversation_workspace_contact_meta"),
    )
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), index=True, nullable=False)
    contact_id = Column(String(36), ForeignKey("contacts.id"), index=True, nullable=False)
    meta_account_id = Column(String(36), ForeignKey("meta_accounts.id"), index=True, nullable=True)
    status = Column(String(32), nullable=False, default="OPEN", index=True)
    priority = Column(String(32), nullable=False, default="NORMAL", index=True)
    assigned_user_id = Column(String(36), ForeignKey("users.id"), index=True, nullable=True)
    last_message_at = Column(DateTime, nullable=True, index=True)
    last_message_preview = Column(String(255), nullable=True, default="")
    unread_count = Column(Integer, nullable=False, default=0)
    is_archived = Column(Boolean, nullable=False, default=False, index=True)
    is_pinned = Column(Boolean, nullable=False, default=False, index=True)
    is_muted = Column(Boolean, nullable=False, default=False)
    is_deleted = Column(Boolean, nullable=False, default=False, index=True)

    workspace = relationship("Workspace")
    contact = relationship("Contact", back_populates="conversations")
    assigned_user = relationship("User", foreign_keys=[assigned_user_id])
    meta_account = relationship("MetaAccount")
    messages = relationship("Message", back_populates="conversation")
