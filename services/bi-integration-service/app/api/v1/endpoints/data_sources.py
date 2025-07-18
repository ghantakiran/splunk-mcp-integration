"""
BI Data Sources endpoints.
"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def get_data_sources():
    """Get data sources."""
    return {"message": "Data sources endpoint - coming soon"}

@router.post("/")
async def create_data_source():
    """Create data source."""
    return {"message": "Create data source endpoint - coming soon"}

@router.get("/{data_source_id}")
async def get_data_source(data_source_id: str):
    """Get data source."""
    return {"message": f"Get data source {data_source_id} - coming soon"}

@router.put("/{data_source_id}")
async def update_data_source(data_source_id: str):
    """Update data source."""
    return {"message": f"Update data source {data_source_id} - coming soon"}

@router.delete("/{data_source_id}")
async def delete_data_source(data_source_id: str):
    """Delete data source."""
    return {"message": f"Delete data source {data_source_id} - coming soon"}