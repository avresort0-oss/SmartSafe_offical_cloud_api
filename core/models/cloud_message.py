from sqlalchemy import Column, String, Text, Boolean

from core.database import Base
from core.models.base import AuditMixin # Import Base from core.database
class CloudMessage(AuditMixin, Base):
    """
    Remote Cloud representation of a synced message.
    Stores strictly encrypted cipher-text.
    """
    __tablename__ = "cloud_messages"
    content = Column(Text, nullable=False)
    sender_id = Column(String(36), index=True, nullable=False)
    workspace_id = Column(String(36), index=True, nullable=False)
    conversation_id = Column(String(36), index=True, nullable=True)
    contact_id = Column(String(36), index=True, nullable=True)
    parent_id = Column(String(36), index=True, nullable=True)
    attachment_path = Column(String(512), nullable=True)
    direction = Column(String(32), nullable=False, default="OUTBOUND")
    channel = Column(String(32), nullable=False, default="LOCAL")
    external_message_id = Column(String(128), nullable=True, index=True)
    is_deleted = Column(Boolean, default=False, index=True)
