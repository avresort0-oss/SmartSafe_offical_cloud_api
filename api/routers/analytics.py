from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from core.database import get_db
from api.dependencies import get_current_workspace
from services.analytics_service import AnalyticsService

router = APIRouter()

@router.get("/summary")
async def get_analytics_summary(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
    workspace = Depends(get_current_workspace)
):
    """Returns a high-level summary of messaging activity."""
    service = AnalyticsService(db)
    return service.get_workspace_summary(workspace.id, days)

@router.get("/performance")
async def get_performance_stats(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
    workspace = Depends(get_current_workspace)
):
    """Returns daily throughput and error distribution."""
    service = AnalyticsService(db)
    return {
        "periodic": service.get_periodic_stats(workspace.id, days),
        "errors": service.get_error_distribution(workspace.id)
    }
