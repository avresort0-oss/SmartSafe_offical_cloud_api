import logging

from celery.signals import task_failure

from core.database import SessionLocal
from core.models.failed_task import FailedTask

logger = logging.getLogger(__name__)


@task_failure.connect
def _record_failed_task(sender=None, task_id=None, exception=None, args=None, kwargs=None, einfo=None, **extra):
    """Centralized dead-letter recorder.

    Fires whenever any Celery task fails terminally -- retries exhausted
    (MaxRetriesExceededError) or no retry policy configured at all -- covering
    every task in workers/message_tasks.py automatically, plus any task added
    later, with no per-task boilerplate required.
    """
    task_name = sender.name if sender is not None else "unknown"
    retries = getattr(getattr(sender, "request", None), "retries", 0)

    db = SessionLocal()
    try:
        db.add(FailedTask(
            task_name=task_name,
            task_id=task_id,
            args_json=list(args) if args else None,
            kwargs_json=dict(kwargs) if kwargs else None,
            exception_message=str(exception)[:2000] if exception else None,
            traceback=einfo.traceback if einfo else None,
            retries=retries or 0,
        ))
        db.commit()
        logger.error(f"Task {task_name} ({task_id}) dead-lettered after {retries} retries: {exception}")
    except Exception:
        db.rollback()
        logger.exception(f"Failed to record dead-lettered task {task_name} ({task_id})")
    finally:
        db.close()
