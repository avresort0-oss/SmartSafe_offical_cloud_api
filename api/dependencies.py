from fastapi import Header, Depends, HTTPException, status
from typing import Optional
from sqlalchemy.orm import Session
from core.database import get_db
from services.auth_service import AuthService
from core.models.workspace import Workspace

async def get_current_workspace(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db)
) -> Workspace:
    """
    Dependency to validate the API key and return the associated workspace.
    Ensures strict tenant isolation for all cloud API requests.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
        
    workspace = AuthService.validate_api_key(db, x_api_key)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return workspace
