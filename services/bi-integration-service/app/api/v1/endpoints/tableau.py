"""
Tableau-specific endpoints.
"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/projects")
async def get_tableau_projects():
    """Get Tableau projects."""
    return {"message": "Tableau projects endpoint - coming soon"}

@router.get("/workbooks")
async def get_tableau_workbooks():
    """Get Tableau workbooks."""
    return {"message": "Tableau workbooks endpoint - coming soon"}

@router.get("/data-sources")
async def get_tableau_data_sources():
    """Get Tableau data sources."""
    return {"message": "Tableau data sources endpoint - coming soon"}

@router.post("/workbooks/{workbook_id}/publish")
async def publish_tableau_workbook(workbook_id: str):
    """Publish Tableau workbook."""
    return {"message": f"Publish Tableau workbook {workbook_id} - coming soon"}

@router.post("/data-sources/{data_source_id}/refresh")
async def refresh_tableau_data_source(data_source_id: str):
    """Refresh Tableau data source."""
    return {"message": f"Refresh Tableau data source {data_source_id} - coming soon"}