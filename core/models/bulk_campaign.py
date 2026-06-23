import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from core.database import Base
from core.models.base import AuditMixin

class BulkCampaign(AuditMixin, Base):
    __tablename__ = "bulk_campaigns"
    
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), index=True, nullable=False)
    name = Column(String(128), nullable=False)
    template_name = Column(String(128), nullable=False)
    language = Column(String(16), nullable=False, default="en_US")
    
    # Comma separated label IDs or names
    target_labels = Column(Text, nullable=True) 
    
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(32), nullable=False, default="PENDING") # PENDING, IN_PROGRESS, COMPLETED, FAILED
    
    total_targets = Column(Integer, default=0)
    sent_count = Column(Integer, default=0)
    
    workspace = relationship("Workspace")

    def __repr__(self):
        return f"<BulkCampaign(id='{self.id}', name='{self.name}', status='{self.status}')>"
