"""
Integration service for managing BI integrations.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.orm import selectinload

from ..core.logging import get_logger
from ..models.bi_models import (
    BIIntegration,
    BIIntegrationCreate,
    BIIntegrationUpdate,
    BIIntegrationResponse,
    BIProvider,
    IntegrationStatus
)
from ..services.tableau_manager import TableauManager
from ..core.redis_client import get_redis_client, RedisBICache

logger = get_logger(__name__)


class IntegrationService:
    """Service for managing BI integrations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.cache = None
    
    async def _get_cache(self) -> RedisBICache:
        """Get Redis cache instance."""
        if not self.cache:
            redis_client = await get_redis_client()
            self.cache = RedisBICache(redis_client)
        return self.cache
    
    async def get_user_integrations(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
        provider: Optional[BIProvider] = None,
        status: Optional[IntegrationStatus] = None
    ) -> List[BIIntegrationResponse]:
        """Get integrations for a user."""
        try:
            query = select(BIIntegration).where(BIIntegration.user_id == user_id)
            
            # Apply filters
            if provider:
                query = query.where(BIIntegration.provider == provider)
            
            if status:
                query = query.where(BIIntegration.status == status)
            
            # Apply pagination
            query = query.offset(skip).limit(limit)
            
            # Order by created_at desc
            query = query.order_by(BIIntegration.created_at.desc())
            
            result = await self.db.execute(query)
            integrations = result.scalars().all()
            
            # Convert to response models
            return [BIIntegrationResponse.from_orm(integration) for integration in integrations]
            
        except Exception as e:
            logger.error(f"Failed to get user integrations: {e}")
            raise
    
    async def get_integration(
        self,
        integration_id: str,
        user_id: str
    ) -> Optional[BIIntegrationResponse]:
        """Get a specific integration."""
        try:
            query = select(BIIntegration).where(
                and_(
                    BIIntegration.id == integration_id,
                    BIIntegration.user_id == user_id
                )
            )
            
            result = await self.db.execute(query)
            integration = result.scalar_one_or_none()
            
            if integration:
                return BIIntegrationResponse.from_orm(integration)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get integration: {e}")
            raise
    
    async def create_integration(
        self,
        user_id: str,
        integration_data: BIIntegrationCreate
    ) -> BIIntegrationResponse:
        """Create a new integration."""
        try:
            # Create integration instance
            integration = BIIntegration(
                user_id=user_id,
                **integration_data.model_dump()
            )
            
            # Add to database
            self.db.add(integration)
            await self.db.commit()
            await self.db.refresh(integration)
            
            # Test connection
            await self._test_integration_connection(integration)
            
            # Update status based on test result
            if integration.status == IntegrationStatus.PENDING:
                integration.status = IntegrationStatus.ACTIVE
                await self.db.commit()
                await self.db.refresh(integration)
            
            logger.info(
                f"Created integration: {integration.id}",
                extra={
                    "user_id": user_id,
                    "integration_id": integration.id,
                    "provider": integration.provider.value
                }
            )
            
            return BIIntegrationResponse.from_orm(integration)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create integration: {e}")
            raise
    
    async def update_integration(
        self,
        integration_id: str,
        user_id: str,
        integration_data: BIIntegrationUpdate
    ) -> Optional[BIIntegrationResponse]:
        """Update an existing integration."""
        try:
            # Get existing integration
            query = select(BIIntegration).where(
                and_(
                    BIIntegration.id == integration_id,
                    BIIntegration.user_id == user_id
                )
            )
            
            result = await self.db.execute(query)
            integration = result.scalar_one_or_none()
            
            if not integration:
                return None
            
            # Update fields
            update_data = integration_data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(integration, field, value)
            
            await self.db.commit()
            await self.db.refresh(integration)
            
            logger.info(
                f"Updated integration: {integration_id}",
                extra={
                    "user_id": user_id,
                    "integration_id": integration_id,
                    "provider": integration.provider.value
                }
            )
            
            return BIIntegrationResponse.from_orm(integration)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update integration: {e}")
            raise
    
    async def delete_integration(
        self,
        integration_id: str,
        user_id: str
    ) -> bool:
        """Delete an integration."""
        try:
            # Check if integration exists
            query = select(BIIntegration).where(
                and_(
                    BIIntegration.id == integration_id,
                    BIIntegration.user_id == user_id
                )
            )
            
            result = await self.db.execute(query)
            integration = result.scalar_one_or_none()
            
            if not integration:
                return False
            
            # Delete integration
            await self.db.delete(integration)
            await self.db.commit()
            
            # Clear cache
            cache = await self._get_cache()
            await cache.invalidate_workbook_cache(integration_id)
            
            logger.info(
                f"Deleted integration: {integration_id}",
                extra={
                    "user_id": user_id,
                    "integration_id": integration_id,
                    "provider": integration.provider.value
                }
            )
            
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to delete integration: {e}")
            raise
    
    async def test_integration(
        self,
        integration_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Test an integration connection."""
        try:
            # Get integration
            query = select(BIIntegration).where(
                and_(
                    BIIntegration.id == integration_id,
                    BIIntegration.user_id == user_id
                )
            )
            
            result = await self.db.execute(query)
            integration = result.scalar_one_or_none()
            
            if not integration:
                return None
            
            # Test connection
            test_result = await self._test_integration_connection(integration)
            
            # Update health status
            integration.health_status = "healthy" if test_result["success"] else "unhealthy"
            if not test_result["success"]:
                integration.last_error = test_result.get("error", "Connection test failed")
            
            await self.db.commit()
            
            logger.info(
                f"Tested integration: {integration_id}",
                extra={
                    "user_id": user_id,
                    "integration_id": integration_id,
                    "provider": integration.provider.value,
                    "success": test_result["success"]
                }
            )
            
            return test_result
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to test integration: {e}")
            raise
    
    async def sync_integration(
        self,
        integration_id: str,
        user_id: str,
        force: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Synchronize an integration."""
        try:
            # Get integration
            query = select(BIIntegration).where(
                and_(
                    BIIntegration.id == integration_id,
                    BIIntegration.user_id == user_id
                )
            )
            
            result = await self.db.execute(query)
            integration = result.scalar_one_or_none()
            
            if not integration:
                return None
            
            # Perform sync based on provider
            sync_result = await self._sync_integration_data(integration, force)
            
            # Update last sync time
            from datetime import datetime
            integration.last_sync_at = datetime.utcnow()
            
            if sync_result["success"]:
                integration.status = IntegrationStatus.ACTIVE
                integration.last_error = None
            else:
                integration.status = IntegrationStatus.ERROR
                integration.last_error = sync_result.get("error", "Sync failed")
            
            await self.db.commit()
            
            logger.info(
                f"Synchronized integration: {integration_id}",
                extra={
                    "user_id": user_id,
                    "integration_id": integration_id,
                    "provider": integration.provider.value,
                    "success": sync_result["success"],
                    "force": force
                }
            )
            
            return sync_result
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to sync integration: {e}")
            raise
    
    async def check_user_access(
        self,
        integration_id: str,
        user_id: str
    ) -> bool:
        """Check if user has access to integration."""
        try:
            query = select(BIIntegration).where(
                and_(
                    BIIntegration.id == integration_id,
                    BIIntegration.user_id == user_id
                )
            )
            
            result = await self.db.execute(query)
            integration = result.scalar_one_or_none()
            
            return integration is not None
            
        except Exception as e:
            logger.error(f"Failed to check user access: {e}")
            raise
    
    async def _test_integration_connection(
        self,
        integration: BIIntegration
    ) -> Dict[str, Any]:
        """Test connection to BI provider."""
        try:
            if integration.provider == BIProvider.TABLEAU:
                manager = TableauManager(integration)
                return await manager.test_connection()
            
            elif integration.provider == BIProvider.POWERBI:
                # TODO: Implement Power BI manager
                return {
                    "success": False,
                    "error": "Power BI integration not yet implemented"
                }
            
            else:
                return {
                    "success": False,
                    "error": f"Provider {integration.provider.value} not supported"
                }
                
        except Exception as e:
            logger.error(f"Integration connection test failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _sync_integration_data(
        self,
        integration: BIIntegration,
        force: bool = False
    ) -> Dict[str, Any]:
        """Synchronize integration data."""
        try:
            if integration.provider == BIProvider.TABLEAU:
                manager = TableauManager(integration)
                
                # Sync projects, workbooks, and data sources
                sync_results = {
                    "projects": 0,
                    "workbooks": 0,
                    "data_sources": 0
                }
                
                # Get projects
                projects = await manager.get_projects()
                sync_results["projects"] = len(projects)
                
                # Get workbooks
                workbooks = await manager.get_workbooks()
                sync_results["workbooks"] = len(workbooks)
                
                # Get data sources
                data_sources = await manager.get_data_sources()
                sync_results["data_sources"] = len(data_sources)
                
                return {
                    "success": True,
                    "sync_results": sync_results,
                    "message": "Sync completed successfully"
                }
            
            elif integration.provider == BIProvider.POWERBI:
                # TODO: Implement Power BI sync
                return {
                    "success": False,
                    "error": "Power BI sync not yet implemented"
                }
            
            else:
                return {
                    "success": False,
                    "error": f"Provider {integration.provider.value} not supported"
                }
                
        except Exception as e:
            logger.error(f"Integration sync failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }