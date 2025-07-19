#!/usr/bin/env python3
"""
API v1 Router for CSV Export Service.

This module provides the main API router that includes all endpoint modules
for the CSV export service.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import csv_export, templates, analytics, jobs

# Create main v1 router
router = APIRouter()

# Include endpoint routers
router.include_router(
    csv_export.router,
    prefix="/export",
    tags=["CSV Export"]
)

router.include_router(
    templates.router,
    prefix="/templates",
    tags=["Templates"]
)

router.include_router(
    analytics.router,
    prefix="/analytics",
    tags=["Analytics"]
)

router.include_router(
    jobs.router,
    prefix="/jobs",
    tags=["Jobs"]
)