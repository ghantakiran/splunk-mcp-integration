"""
API v1 router configuration for Unified Authentication Bridge
"""

from fastapi import APIRouter
from .endpoints import auth, status

api_router = APIRouter()

# Authentication endpoints
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])

# Status and monitoring endpoints
api_router.include_router(status.router, prefix="/status", tags=["status"])