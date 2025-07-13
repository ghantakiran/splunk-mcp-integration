"""
API v1 router configuration
"""

from fastapi import APIRouter
from .endpoints import (
    health,
    auth,
    users,
    chat,
    queries,
    dashboards,
    alerts,
    system,
    demo_exceptions
)

api_router = APIRouter()

# Health and system endpoints
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(system.router, prefix="/system", tags=["system"])

# Authentication endpoints
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])

# User management endpoints
api_router.include_router(users.router, prefix="/users", tags=["users"])

# Chat and conversation endpoints
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])

# Query management endpoints
api_router.include_router(queries.router, prefix="/queries", tags=["queries"])

# Dashboard endpoints
api_router.include_router(dashboards.router, prefix="/dashboards", tags=["dashboards"])

# Alert management endpoints
api_router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])

# Demo endpoints (only in development)
if True:  # Would check settings.debug in production
    api_router.include_router(demo_exceptions.router, prefix="/demo", tags=["demo"])