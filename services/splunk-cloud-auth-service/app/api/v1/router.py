"""
API router for Splunk Cloud Authentication Service
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, oauth, health, tenants

# Create main API router
api_router = APIRouter()

# Include endpoint routers
api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(oauth.router, prefix="/oauth", tags=["OAuth 2.0"])
api_router.include_router(tenants.router, prefix="/tenants", tags=["Multi-Tenant"])