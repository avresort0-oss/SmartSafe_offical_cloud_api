import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String, Table, UniqueConstraint
from sqlalchemy.orm import relationship

from core.database import Base
from core.models.base import AuditMixin


conversation_labels = Table(
    "conversation_labels",
    Base.metadata,
    Column("conversation_id", String(36), ForeignKey("conversations.id"), primary_key=True),
    Column("label_id", String(36), ForeignKey("labels.id"), primary_key=True)
)

contact_labels = Table(
    "contact_labels",
    Base.metadata,
    Column("contact_id", String(36), ForeignKey("contacts.id"), primary_key=True),
    Column("label_id", String(36), ForeignKey("labels.id"), primary_key=True)
)

class Label(AuditMixin, Base):
    __tablename__ = "labels"
    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uq_labels_workspace_name"),
    )
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), index=True, nullable=False)
    name = Column(String(64), nullable=False)
    color_hex = Column(String(16), nullable=False, default="#00a884")
    applies_to = Column(String(32), nullable=False, default="BOTH")
    workspace = relationship("Workspace")
    conversations = relationship("Conversation", secondary=conversation_labels, backref="labels")
    contacts = relationship("Contact", secondary=contact_labels, backref="labels")
