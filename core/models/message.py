from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import sys
import uuid

from core.database import Base
from core.models.base import AuditMixin

class Message(AuditMixin, Base):
    __tablename__ = "messages"
    content = Column(Text, nullable=False)
    sender_id = Column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), index=True, nullable=False)
    conversation_id = Column(String(36), ForeignKey("conversations.id"), index=True, nullable=True)
    contact_id = Column(String(36), ForeignKey("contacts.id"), index=True, nullable=True)
    parent_id = Column(String(36), ForeignKey("messages.id"), index=True, nullable=True) # For threading
    attachment_path = Column(String(512), nullable=True)
    direction = Column(String(32), nullable=False, default="OUTBOUND", index=True)
    channel = Column(String(32), nullable=False, default="LOCAL", index=True)
    external_message_id = Column(String(128), nullable=True, index=True)
    is_synced = Column(Boolean, default=False, index=True) # Flag for offline-first sync
    is_deleted = Column(Boolean, default=False, index=True) # Soft delete flag
    is_starred = Column(Boolean, default=False, index=True) # Starred message flag
    status = Column(String(32), nullable=False, default="PENDING", index=True) # PENDING, QUEUED, SENT, DELIVERED, READ, FAILED
    provider_error_code = Column(String(64), nullable=True) # WhatsApp error code
    media_id = Column(String(128), nullable=True)
    media_type = Column(String(32), nullable=True) # image, video, audio, document
    media_url = Column(Text, nullable=True) # Public URL or signed URL for the media
    # Relationships
    sender = relationship("User", back_populates="sent_messages", foreign_keys=[sender_id])
    workspace = relationship("Workspace", back_populates="messages")
    conversation = relationship("Conversation", back_populates="messages")
    contact = relationship("Contact")
    parent_message = relationship("Message", remote_side="Message.id", back_populates="replies")
    replies = relationship("Message", back_populates="parent_message")

    def __repr__(self):
        return f"<Message(id='{self.id}', sender_id='{self.sender_id}', workspace_id='{self.workspace_id}', content='{self.content[:30]}...')>"
