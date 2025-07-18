"""
Main API router for BI Integration Service v1.
"""

from fastapi import APIRouter

from .endpoints import (
    integrations,
    data_sources,
    workbooks,
    dashboards,
    reports,
    users,
    analytics,
    tableau,
    powerbi
)

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(
    integrations.router,
    prefix="/integrations",
    tags=["integrations"],
)

api_router.include_router(
    data_sources.router,
    prefix="/data-sources",
    tags=["data-sources"],
)

api_router.include_router(
    workbooks.router,
    prefix="/workbooks",
    tags=["workbooks"],
)

api_router.include_router(
    dashboards.router,
    prefix="/dashboards",
    tags=["dashboards"],
)

api_router.include_router(
    reports.router,
    prefix="/reports",
    tags=["reports"],
)

api_router.include_router(
    users.router,
    prefix="/users",
    tags=["users"],
)

api_router.include_router(
    analytics.router,
    prefix="/analytics",
    tags=["analytics"],
)

api_router.include_router(
    tableau.router,
    prefix="/tableau",
    tags=["tableau"],
)

api_router.include_router(
    powerbi.router,
    prefix="/powerbi",
    tags=["powerbi"],
)