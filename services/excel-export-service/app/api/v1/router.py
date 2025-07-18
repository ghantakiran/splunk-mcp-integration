"""
API v1 router.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import excel_exports


# Create API router
api_router = APIRouter()

# Include endpoint routers
api_router.include_router(
    excel_exports.router,
    prefix="/excel-exports",
    tags=["excel-exports"]
)