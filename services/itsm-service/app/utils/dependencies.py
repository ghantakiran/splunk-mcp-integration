"""
Dependency injection utilities for ITSM Service.
"""

from typing import Dict, Any
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..core.database import get_database
from ..models.itsm_models import ITSMIntegration
from ..services.servicenow_manager import ServiceNowManager
from ..services.jira_manager import JiraManager
from ..services.workflow_engine import WorkflowEngine
from ..services.sync_manager import SyncManager
from .auth import User, get_current_user

# Global instances
_workflow_engine = None
_sync_manager = None


async def get_servicenow_manager(
    integration_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
) -> ServiceNowManager:
    """Get ServiceNow manager for specific integration."""
    
    # Get integration
    stmt = select(ITSMIntegration).where(
        ITSMIntegration.id == integration_id,
        ITSMIntegration.user_id == current_user.id,
        ITSMIntegration.provider == "servicenow"
    )
    result = await db.execute(stmt)
    integration = result.scalar_one_or_none()
    
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ServiceNow integration not found"
        )
    
    if not integration.active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ServiceNow integration is not active"
        )
    
    return ServiceNowManager(integration)


async def get_jira_manager(
    integration_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
) -> JiraManager:
    """Get Jira manager for specific integration."""
    
    # Get integration
    stmt = select(ITSMIntegration).where(
        ITSMIntegration.id == integration_id,
        ITSMIntegration.user_id == current_user.id,
        ITSMIntegration.provider == "jira"
    )
    result = await db.execute(stmt)
    integration = result.scalar_one_or_none()
    
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Jira integration not found"
        )
    
    if not integration.active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Jira integration is not active"
        )
    
    return JiraManager(integration)


async def get_integration_manager(
    integration_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
) -> Any:
    """Get appropriate manager based on integration provider."""
    
    # Get integration
    stmt = select(ITSMIntegration).where(
        ITSMIntegration.id == integration_id,
        ITSMIntegration.user_id == current_user.id
    )
    result = await db.execute(stmt)
    integration = result.scalar_one_or_none()
    
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found"
        )
    
    if not integration.active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Integration is not active"
        )
    
    if integration.provider.value == "servicenow":
        return ServiceNowManager(integration)
    elif integration.provider.value == "jira":
        return JiraManager(integration)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported provider: {integration.provider.value}"
        )


async def get_workflow_engine() -> WorkflowEngine:
    """Get workflow engine instance."""
    global _workflow_engine
    
    if _workflow_engine is None:
        _workflow_engine = WorkflowEngine()
    
    return _workflow_engine


async def get_sync_manager(
    db: AsyncSession = Depends(get_database)
) -> SyncManager:
    """Get sync manager instance."""
    global _sync_manager
    
    if _sync_manager is None:
        _sync_manager = SyncManager(db)
    else:
        # Update database session
        _sync_manager.db_session = db
    
    return _sync_manager


async def get_user_integration(
    integration_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
) -> ITSMIntegration:
    """Get user's ITSM integration."""
    
    stmt = select(ITSMIntegration).where(
        ITSMIntegration.id == integration_id,
        ITSMIntegration.user_id == current_user.id
    )
    result = await db.execute(stmt)
    integration = result.scalar_one_or_none()
    
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found"
        )
    
    return integration


async def validate_integration_access(
    integration_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
) -> ITSMIntegration:
    """Validate user has access to integration."""
    
    stmt = select(ITSMIntegration).where(
        ITSMIntegration.id == integration_id
    )
    result = await db.execute(stmt)
    integration = result.scalar_one_or_none()
    
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found"
        )
    
    # Check if user has access (owner or admin)
    if (integration.user_id != current_user.id and 
        "itsm_admin" not in current_user.roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this integration"
        )
    
    return integration


class ManagerProvider:
    """Provider for getting appropriate manager based on integration."""
    
    def __init__(self, integration: ITSMIntegration):
        self.integration = integration
        self._manager = None
    
    def get_manager(self):
        """Get appropriate manager for the integration."""
        if self._manager is None:
            if self.integration.provider.value == "servicenow":
                self._manager = ServiceNowManager(self.integration)
            elif self.integration.provider.value == "jira":
                self._manager = JiraManager(self.integration)
            else:
                raise ValueError(f"Unsupported provider: {self.integration.provider.value}")
        
        return self._manager


async def get_manager_provider(
    integration_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
) -> ManagerProvider:
    """Get manager provider for integration."""
    
    integration = await get_user_integration(integration_id, current_user, db)
    return ManagerProvider(integration)


# Utility functions for common operations
async def check_integration_health(
    integration: ITSMIntegration
) -> Dict[str, Any]:
    """Check health of an integration."""
    
    try:
        if integration.provider.value == "servicenow":
            manager = ServiceNowManager(integration)
        elif integration.provider.value == "jira":
            manager = JiraManager(integration)
        else:
            return {
                "healthy": False,
                "error": f"Unsupported provider: {integration.provider.value}"
            }
        
        # Test connection
        healthy, message = await manager.test_connection()
        
        return {
            "healthy": healthy,
            "message": message,
            "last_checked": "now"
        }
        
    except Exception as e:
        return {
            "healthy": False,
            "error": str(e),
            "last_checked": "now"
        }


async def get_integration_capabilities(
    integration: ITSMIntegration
) -> Dict[str, Any]:
    """Get capabilities of an integration."""
    
    capabilities = {
        "provider": integration.provider.value,
        "bidirectional_sync": integration.bidirectional_sync,
        "sync_enabled": integration.sync_enabled,
        "features": []
    }
    
    if integration.provider.value == "servicenow":
        capabilities["features"] = [
            "incidents",
            "problems", 
            "change_requests",
            "service_requests",
            "knowledge_base",
            "cmdb"
        ]
    elif integration.provider.value == "jira":
        capabilities["features"] = [
            "issues",
            "projects",
            "workflows", 
            "custom_fields",
            "attachments",
            "comments"
        ]
    
    return capabilities


# Dependency for getting authenticated integration managers
def require_servicenow_manager(integration_id: str):
    """Dependency factory for ServiceNow manager."""
    
    async def _get_manager(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_database)
    ) -> ServiceNowManager:
        return await get_servicenow_manager(integration_id, current_user, db)
    
    return _get_manager


def require_jira_manager(integration_id: str):
    """Dependency factory for Jira manager."""
    
    async def _get_manager(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_database)
    ) -> JiraManager:
        return await get_jira_manager(integration_id, current_user, db)
    
    return _get_manager


def require_integration_manager(integration_id: str):
    """Dependency factory for integration manager."""
    
    async def _get_manager(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_database)
    ) -> Any:
        return await get_integration_manager(integration_id, current_user, db)
    
    return _get_manager