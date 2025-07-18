"""
API router for PDF Export Service v1.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import pdf_exports, templates

# Create main API router
api_router = APIRouter()

# Include endpoint routers
api_router.include_router(pdf_exports.router)
api_router.include_router(templates.router)

# Health check endpoint
@api_router.get("/health")
async def health_check():
    """Basic health check."""
    return {
        "status": "healthy",
        "service": "pdf-export-service",
        "version": "1.0.0"
    }


# Service info endpoint
@api_router.get("/info")
async def service_info():
    """Get service information."""
    return {
        "name": "PDF Export Service",
        "version": "1.0.0",
        "description": "Advanced PDF generation service for Splunk MCP platform",
        "endpoints": [
            {
                "path": "/pdf-exports",
                "description": "PDF export operations"
            },
            {
                "path": "/templates",
                "description": "Template management operations"
            }
        ]
    }