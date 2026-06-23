import os
import sys
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from api.routers import messages_router, templates_router, analytics_router, accounts_router, integration_router, webhooks_router
from api.middleware import rate_limit_middleware
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI(
    title="SmartSafe Cloud API",
    description="Enterprise Meta Cloud API Orchestration Layer",
    version="1.0.0"
)

app.add_middleware(BaseHTTPMiddleware, dispatch=rate_limit_middleware)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(messages_router, prefix="/v1/messages", tags=["Messages"])
app.include_router(templates_router, prefix="/v1/templates", tags=["Templates"])
app.include_router(analytics_router, prefix="/v1/analytics", tags=["Analytics"])
app.include_router(accounts_router, prefix="/v1/accounts", tags=["Accounts"])
app.include_router(integration_router, prefix="/v1/settings", tags=["Settings"])
app.include_router(webhooks_router, prefix="/webhook", tags=["Webhooks"])

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "SmartSafe API"}

if __name__ == "__main__":
    port = int(os.getenv("API_PORT", 8000))
    uvicorn.run("api_main:app", host="0.0.0.0", port=port, reload=True)
