"""
BI Users endpoints.
"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def get_users():
    """Get users."""
    return {"message": "Users endpoint - coming soon"}

@router.post("/")
async def create_user():
    """Create user."""
    return {"message": "Create user endpoint - coming soon"}

@router.get("/{user_id}")
async def get_user(user_id: str):
    """Get user."""
    return {"message": f"Get user {user_id} - coming soon"}

@router.put("/{user_id}")
async def update_user(user_id: str):
    """Update user."""
    return {"message": f"Update user {user_id} - coming soon"}

@router.delete("/{user_id}")
async def delete_user(user_id: str):
    """Delete user."""
    return {"message": f"Delete user {user_id} - coming soon"}