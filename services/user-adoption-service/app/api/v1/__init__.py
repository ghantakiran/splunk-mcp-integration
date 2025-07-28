#!/usr/bin/env python3
"""
API v1 Package
==============
Version 1 of the User Adoption Service API
"""

from fastapi import APIRouter
from .endpoints import onboarding, feedback, adoption

# Create API router
api_router = APIRouter()

# Include endpoint routers
api_router.include_router(onboarding.router, prefix="/onboarding", tags=["onboarding"])
api_router.include_router(feedback.router, prefix="/feedback", tags=["feedback"])
api_router.include_router(adoption.router, prefix="/adoption", tags=["adoption"])

__all__ = ["api_router"]