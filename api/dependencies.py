import os
import secrets
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

async def require_internal_ops_access(
    x_internal_key: Optional[str] = Header(None, alias="X-Internal-Key"),
) -> None:
    """
    Dependency for operator-only endpoints that are NOT tenant data (e.g. the
    Celery dead-letter queue, which has no workspace_id and can reference any
    tenant's records). Deliberately separate from get_current_workspace's
    per-tenant API keys -- a tenant's key must never grant access here.

    Gated by the INTERNAL_OPS_KEY environment variable, intended to be held only
    by operator/ops tooling, never distributed to tenants. If the env var isn't
    configured, the endpoint is unreachable (fails closed) rather than open.
    """
    expected = os.getenv("INTERNAL_OPS_KEY")
    if not expected or not x_internal_key or not secrets.compare_digest(x_internal_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid internal ops key",
            headers={"WWW-Authenticate": "InternalKey"},
        )
