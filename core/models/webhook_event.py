from sqlalchemy import Column, String, Text
from core.database import Base
from core.models.base import AuditMixin

class WebhookEvent(AuditMixin, Base):
    __tablename__ = "webhook_events"

    payload_hash = Column(String(64), unique=True, index=True, nullable=False)
    phone_number_id = Column(String(64), index=True, nullable=True)
    status = Column(String(32), default="PENDING", index=True, nullable=False)
    error_message = Column(Text, nullable=True)
    raw_payload = Column(Text, nullable=False)

    def __repr__(self):
        return f"<WebhookEvent(id='{self.id}', status='{self.status}', hash='{self.payload_hash}')>"
