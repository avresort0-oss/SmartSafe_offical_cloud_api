import os
from celery import Celery

# Load Redis URL from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Initialize Celery
app = Celery(
    "smartsafe_workers",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["workers.message_tasks", "workers.dlq"]
)

# Optional configuration
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True
)

# Import directly (in addition to `include` above) so the task_failure signal
# handler is registered as soon as this module loads, regardless of whether the
# importer is a real worker process, the API server, or a test -- `include` alone
# only guarantees import once the worker actually bootstraps.
from . import dlq  # noqa: E402,F401

if __name__ == "__main__":
    app.start()

app.conf.beat_schedule = {
    "check-sla-breaches": {
        "task": "workers.message_tasks.check_sla_breaches",
        "schedule": 300.0, # Every 5 minutes
    },
    "process-scheduled-campaigns": {
        "task": "workers.message_tasks.process_scheduled_campaigns",
        "schedule": 60.0, # Every 1 minute
    },
}
