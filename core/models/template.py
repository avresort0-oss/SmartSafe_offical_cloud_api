from sqlalchemy import Column, String, ForeignKey, JSON
from core.database import Base
from core.models.base import AuditMixin

class Template(AuditMixin, Base):
    """
    Stores synchronized WhatsApp message templates from Meta Cloud API.
    Enables rapid lookup and UI selection without constant API round-trips.
    """
    __tablename__ = "templates"
    
    id = Column(String, primary_key=True) # Meta's template ID
    name = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False)   # e.g., "APPROVED", "PENDING", "REJECTED"
    category = Column(String, nullable=False) # e.g., "MARKETING", "UTILITY"
    language = Column(String, nullable=False)
    components_json = Column(JSON, nullable=False) # Stores the structure
    
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    meta_account_id = Column(String(36), ForeignKey("meta_accounts.id"), nullable=False, index=True)
