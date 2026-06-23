from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from core.models.meta_account import MetaAccount
from api.dependencies import get_current_workspace
from services.meta_cloud_service import MetaCloudService
from datetime import datetime, timezone

router = APIRouter()

@router.get("/{account_id}/health")
async def get_account_health(
    account_id: str,
    db: Session = Depends(get_db),
    workspace = Depends(get_current_workspace)
):
    """Fetches real-time quality rating and status from Meta."""
    account = db.query(MetaAccount).filter(
        MetaAccount.id == account_id,
        MetaAccount.workspace_id == workspace.id
    ).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Meta Account not found")
        
    meta_service = MetaCloudService()
    info, error = meta_service.get_phone_info(account.phone_number_id, account.access_token)
    
    if error:
        raise HTTPException(status_code=400, detail=f"Meta API error: {error}")
        
    # Update local cache
    account.quality_rating = info.quality_rating
    account.api_status = info.api_status
    account.display_phone = info.display_phone_number
    account.verified_name = info.verified_name
    account.last_synced_at = datetime.now(timezone.utc)
    db.commit()
    
    return {
        "id": account.id,
        "api_status": account.api_status,
        "quality_rating": account.quality_rating,
        "display_phone": account.display_phone,
        "verified_name": account.verified_name,
        "last_synced_at": account.last_synced_at
    }
