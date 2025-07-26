"""
API router for Cloud Connection Manager Service.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import connections, load_balancer, health

# Create main API router
api_router = APIRouter()

# Include endpoint routers
api_router.include_router(
    connections.router,
    prefix="/connections",
    tags=["connections"],
    responses={404: {"description": "Not found"}}
)

api_router.include_router(
    load_balancer.router,
    prefix="/load-balancer",
    tags=["load-balancer"],
    responses={404: {"description": "Not found"}}
)

api_router.include_router(
    health.router,
    prefix="/health",
    tags=["health"],
    responses={404: {"description": "Not found"}}
)