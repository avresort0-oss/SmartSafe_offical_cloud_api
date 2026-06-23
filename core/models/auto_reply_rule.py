from sqlalchemy import Boolean, Column, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, AuditMixin

class AutoReplyRule(Base, AuditMixin):
    __tablename__ = "auto_reply_rules"

    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), nullable=False)
    trigger_keyword: Mapped[str] = mapped_column(String(255), nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(50), default="exact") # exact, contains, starts_with
    response_text: Mapped[str] = mapped_column(String(2000), nullable=False)
    attachment_path: Mapped[str] = mapped_column(String(511), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Optional: meta_account_id if we want to restrict rule to specific WhatsApp profile
    meta_account_id: Mapped[str] = mapped_column(String(36), nullable=True) 
