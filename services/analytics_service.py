import logging
from typing import Dict, List, Any
from datetime import datetime, timedelta
from sqlalchemy import func, and_
from sqlalchemy.orm import Session
from core.models.message import Message

logger = logging.getLogger(__name__)

class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def get_workspace_summary(self, workspace_id: str, days: int = 7) -> Dict[str, Any]:
        """
        Returns a high-level summary of messaging activity for the dashboard.
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Aggregate status counts
        stats = self.db.query(
            Message.status, 
            func.count(Message.id)
        ).filter(
            and_(
                Message.workspace_id == workspace_id,
                Message.created_at >= start_date
            )
        ).group_by(Message.status).all()
        
        summary = {s[0].lower() if s[0] else "unknown": s[1] for s in stats}
        summary["total"] = sum(summary.values())
        
        # Calculate delivery rate
        sent = summary.get("sent", 0) + summary.get("delivered", 0) + summary.get("read", 0)
        delivered = summary.get("delivered", 0) + summary.get("read", 0)
        
        summary["delivery_rate"] = (delivered / sent * 100) if sent > 0 else 0
        summary["days_period"] = days
        
        return summary

    def get_periodic_stats(self, workspace_id: str, days: int = 7) -> List[Dict[str, Any]]:
        """
        Returns daily message counts for charts.
        """
        start_date = (datetime.utcnow() - timedelta(days=days)).date()
        
        # SQLite specific date grouping
        stats = self.db.query(
            func.date(Message.created_at).label("day"),
            func.count(Message.id).label("count")
        ).filter(
            and_(
                Message.workspace_id == workspace_id,
                func.date(Message.created_at) >= start_date
            )
        ).group_by("day").order_by("day").all()
        
        return [{"date": s.day, "count": s.count} for s in stats]

    def get_error_distribution(self, workspace_id: str) -> List[Dict[str, Any]]:
        """
        Returns distribution of failed messages by provider error code.
        """
        errors = self.db.query(
            Message.provider_error_code,
            func.count(Message.id)
        ).filter(
            and_(
                Message.workspace_id == workspace_id,
                Message.status == "FAILED"
            )
        ).group_by(Message.provider_error_code).all()
        
        return [{"error_code": e[0] or "UNKNOWN", "count": e[1]} for e in errors]
