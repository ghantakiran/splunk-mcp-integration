"""
BI Analytics endpoints.
"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def get_analytics():
    """Get analytics."""
    return {"message": "Analytics endpoint - coming soon"}

@router.get("/usage")
async def get_usage_analytics():
    """Get usage analytics."""
    return {"message": "Usage analytics endpoint - coming soon"}

@router.get("/performance")
async def get_performance_analytics():
    """Get performance analytics."""
    return {"message": "Performance analytics endpoint - coming soon"}