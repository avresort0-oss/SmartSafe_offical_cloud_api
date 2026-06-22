from sqlalchemy import Column, String, Integer, Text, JSON
from core.database import Base
from core.models.base import AuditMixin

class FailedTask(AuditMixin, Base):
    """
    Dead-letter record for a Celery task that failed terminally -- either its
    retries were exhausted (dispatch_whatsapp_message, download_incoming_media)
    or it raised without any retry policy (check_sla_breaches,
    process_scheduled_campaigns). Populated centrally by the task_failure signal
    handler in workers/dlq.py, so any task added later is covered automatically.
    """
    __tablename__ = "failed_tasks"

    task_name = Column(String(255), nullable=False, index=True)
    task_id = Column(String(64), nullable=True, index=True)
    args_json = Column(JSON, nullable=True)
    kwargs_json = Column(JSON, nullable=True)
    exception_message = Column(Text, nullable=True)
    traceback = Column(Text, nullable=True)
    retries = Column(Integer, nullable=False, default=0)
    status = Column(String(32), nullable=False, default="DEAD_LETTERED", index=True) # DEAD_LETTERED, REVIEWED, RESOLVED

    def __repr__(self):
        return f"<FailedTask(id='{self.id}', task_name='{self.task_name}', status='{self.status}')>"
