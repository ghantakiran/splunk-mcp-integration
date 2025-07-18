#!/usr/bin/env python3
"""
API router for PowerPoint Export Service v1.

This module defines the main API router that includes all endpoint routers
for version 1 of the PowerPoint export service API.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    powerpoint_exports,
    templates,
    health
)


# Create the main API router
api_router = APIRouter()

# Include endpoint routers
api_router.include_router(
    powerpoint_exports.router,
    prefix="/powerpoint-exports",
    tags=["PowerPoint Exports"]
)

api_router.include_router(
    templates.router,
    prefix="/templates",
    tags=["Templates"]
)

api_router.include_router(
    health.router,
    prefix="/health",
    tags=["Health"]
)


# Export the router
__all__ = ["api_router"]
