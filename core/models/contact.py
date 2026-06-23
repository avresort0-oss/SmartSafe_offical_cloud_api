import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from core.database import Base
from core.models.base import AuditMixin


class Contact(AuditMixin, Base):
    __tablename__ = "contacts"
    __table_args__ = (
        UniqueConstraint("workspace_id", "phone_e164", name="uq_contacts_workspace_phone"),
    )
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), index=True, nullable=False)
    phone_e164 = Column(String(32), nullable=False, index=True)
    display_name = Column(String(120), nullable=False, default="Unknown")
    email = Column(String(120), nullable=True)
    lifecycle_stage = Column(String(32), nullable=False, default="LEAD")
    owner_user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    notes = Column(Text, nullable=True, default="")
    is_whatsapp_customer = Column(Boolean, default=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    workspace = relationship("Workspace")
    owner = relationship("User", foreign_keys=[owner_user_id])
    conversations = relationship("Conversation", back_populates="contact")
    contracts = relationship("Contract", back_populates="contact")
