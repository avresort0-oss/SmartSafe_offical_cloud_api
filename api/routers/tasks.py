from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.dependencies import require_internal_ops_access
from core.database import get_db
from core.models.failed_task import FailedTask

router = APIRouter()


class FailedTaskResponse(BaseModel):
    id: str
    task_name: str
    task_id: Optional[str]
    args_json: Optional[list]
    kwargs_json: Optional[dict]
    exception_message: Optional[str]
    retries: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/failed", response_model=List[FailedTaskResponse], dependencies=[Depends(require_internal_ops_access)])
async def list_failed_tasks(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    task_name: Optional[str] = Query(None),
):
    """Lists dead-lettered Celery tasks, most recent first. Operator-only (see
    require_internal_ops_access) since FailedTask spans every tenant."""
    q = db.query(FailedTask)
    if task_name:
        q = q.filter(FailedTask.task_name == task_name)
    return q.order_by(FailedTask.created_at.desc()).offset(offset).limit(limit).all()
