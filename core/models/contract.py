import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from core.database import Base
from core.models.base import AuditMixin


class Contract(AuditMixin, Base):
    __tablename__ = "contracts"
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), index=True, nullable=False)
    contact_id = Column(String(36), ForeignKey("contacts.id"), index=True, nullable=False)
    title = Column(String(180), nullable=False)
    contract_number = Column(String(80), nullable=True, index=True)
    contract_type = Column(String(80), nullable=True, default="SERVICE")
    status = Column(String(32), nullable=False, default="DRAFT", index=True)
    value_amount = Column(Float, nullable=True)
    currency = Column(String(12), nullable=False, default="USD")
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    renewal_date = Column(Date, nullable=True)
    reminder_days_before = Column(Integer, nullable=False, default=30)
    document_path = Column(String(512), nullable=True)
    owner_user_id = Column(String(36), ForeignKey("users.id"), index=True, nullable=True)
    notes = Column(Text, nullable=True, default="")
    workspace = relationship("Workspace")
    contact = relationship("Contact", back_populates="contracts")
    owner = relationship("User", foreign_keys=[owner_user_id])
