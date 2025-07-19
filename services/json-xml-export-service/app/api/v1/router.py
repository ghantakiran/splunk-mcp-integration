"""
API v1 router configuration.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import json_xml_exports

# Create API router
router = APIRouter()

# Include endpoint routers
router.include_router(
    json_xml_exports.router,
    prefix="/json-xml-exports",
    tags=["JSON/XML Exports"]
)