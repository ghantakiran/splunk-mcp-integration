"""
BI Dashboards endpoints.
"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def get_dashboards():
    """Get dashboards."""
    return {"message": "Dashboards endpoint - coming soon"}

@router.post("/")
async def create_dashboard():
    """Create dashboard."""
    return {"message": "Create dashboard endpoint - coming soon"}

@router.get("/{dashboard_id}")
async def get_dashboard(dashboard_id: str):
    """Get dashboard."""
    return {"message": f"Get dashboard {dashboard_id} - coming soon"}

@router.put("/{dashboard_id}")
async def update_dashboard(dashboard_id: str):
    """Update dashboard."""
    return {"message": f"Update dashboard {dashboard_id} - coming soon"}

@router.delete("/{dashboard_id}")
async def delete_dashboard(dashboard_id: str):
    """Delete dashboard."""
    return {"message": f"Delete dashboard {dashboard_id} - coming soon"}