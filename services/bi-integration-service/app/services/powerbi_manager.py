"""
Power BI integration manager.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import httpx
from msal import ConfidentialClientApplication

from ..core.config import settings
from ..core.logging import get_logger, add_powerbi_context, add_performance_context
from ..models.bi_models import BIIntegration, BIWorkbook, BIDataSource, PublishStatus

logger = get_logger(__name__)


class PowerBIManager:
    """Power BI integration manager."""
    
    def __init__(self, integration: BIIntegration):
        self.integration = integration
        self.client = None
        self._token = None
        self._token_expires_at = None
        
        # Initialize Power BI configuration
        self.tenant_id = integration.credentials.get("tenant_id") or settings.powerbi_tenant_id
        self.client_id = integration.credentials.get("client_id") or settings.powerbi_client_id
        self.client_secret = integration.credentials.get("client_secret") or settings.powerbi_client_secret
        self.scope = integration.credentials.get("scope", settings.powerbi_scope)
        
        # API configuration
        self.api_url = settings.powerbi_api_url
        self.authority = f"{settings.powerbi_authority}{self.tenant_id}"
        self.timeout = settings.powerbi_timeout
        self.max_retries = settings.powerbi_max_retries
        
        # Initialize MSAL client
        self.msal_client = ConfidentialClientApplication(
            self.client_id,
            authority=self.authority,
            client_credential=self.client_secret,
        )
        
        # Initialize HTTP client
        self.http_client = httpx.AsyncClient(
            timeout=self.timeout,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        )
    
    async def authenticate(self) -> bool:
        """Authenticate with Power BI using OAuth 2.0."""
        try:
            # Check if token is still valid
            if self._token and self._token_expires_at:
                if datetime.now() < self._token_expires_at:
                    return True
            
            # Get new token
            result = self.msal_client.acquire_token_for_client(scopes=self.scope)
            
            if "access_token" in result:
                self._token = result["access_token"]
                
                # Calculate expiration time
                expires_in = result.get("expires_in", 3600)
                self._token_expires_at = datetime.now() + timedelta(seconds=expires_in - 60)
                
                # Update HTTP client headers
                self.http_client.headers["Authorization"] = f"Bearer {self._token}"
                
                logger.info(
                    "Power BI authentication successful",
                    **add_powerbi_context(
                        workspace_id="system"
                    )
                )
                
                return True
            else:
                error = result.get("error_description", "Unknown error")
                logger.error(
                    f"Power BI authentication failed: {error}",
                    **add_powerbi_context(
                        workspace_id="system"
                    )
                )
                return False
                
        except Exception as e:
            logger.error(
                f"Power BI authentication error: {e}",
                **add_powerbi_context(
                    workspace_id="system"
                )
            )
            return False
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to Power BI."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            if not await self.authenticate():
                return {
                    "success": False,
                    "error": "Authentication failed",
                    "details": "Could not authenticate with Power BI"
                }
            
            # Test by getting workspaces
            response = await self.http_client.get(f"{self.api_url}v1.0/myorg/groups")
            
            if response.status_code == 200:
                workspaces = response.json()
                duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
                
                logger.info(
                    "Power BI connection test successful",
                    **add_performance_context(
                        operation="connection_test",
                        duration_ms=duration_ms
                    ),
                    **add_powerbi_context(
                        workspace_id="system"
                    )
                )
                
                return {
                    "success": True,
                    "workspaces_count": len(workspaces.get("value", [])),
                    "response_time_ms": duration_ms
                }
            else:
                duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
                
                logger.error(
                    f"Power BI connection test failed: {response.status_code}",
                    **add_performance_context(
                        operation="connection_test",
                        duration_ms=duration_ms,
                        success=False
                    ),
                    **add_powerbi_context(
                        workspace_id="system"
                    )
                )
                
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "details": response.text,
                    "response_time_ms": duration_ms
                }
                
        except Exception as e:
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            
            logger.error(
                f"Power BI connection test error: {e}",
                **add_performance_context(
                    operation="connection_test",
                    duration_ms=duration_ms,
                    success=False,
                    error_type=type(e).__name__
                ),
                **add_powerbi_context(
                    workspace_id="system"
                )
            )
            
            return {
                "success": False,
                "error": str(e),
                "response_time_ms": duration_ms
            }
    
    async def get_workspaces(self) -> List[Dict[str, Any]]:
        """Get list of workspaces from Power BI."""
        try:
            if not await self.authenticate():
                raise Exception("Authentication failed")
            
            response = await self.http_client.get(f"{self.api_url}v1.0/myorg/groups")
            
            if response.status_code == 200:
                data = response.json()
                workspaces = []
                
                for workspace in data.get("value", []):
                    workspaces.append({
                        "id": workspace.get("id"),
                        "name": workspace.get("name"),
                        "type": workspace.get("type"),
                        "state": workspace.get("state"),
                        "is_read_only": workspace.get("isReadOnly", False),
                        "is_on_dedicated_capacity": workspace.get("isOnDedicatedCapacity", False),
                        "capacity_id": workspace.get("capacityId"),
                        "description": workspace.get("description", "")
                    })
                
                logger.info(
                    f"Retrieved {len(workspaces)} Power BI workspaces",
                    **add_powerbi_context(
                        workspace_id="system"
                    )
                )
                
                return workspaces
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            logger.error(
                f"Failed to get Power BI workspaces: {e}",
                **add_powerbi_context(
                    workspace_id="system"
                )
            )
            raise
    
    async def get_reports(self, workspace_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of reports from Power BI."""
        try:
            if not await self.authenticate():
                raise Exception("Authentication failed")
            
            # Use default workspace if not specified
            if workspace_id:
                url = f"{self.api_url}v1.0/myorg/groups/{workspace_id}/reports"
            else:
                url = f"{self.api_url}v1.0/myorg/reports"
            
            response = await self.http_client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                reports = []
                
                for report in data.get("value", []):
                    reports.append({
                        "id": report.get("id"),
                        "name": report.get("name"),
                        "web_url": report.get("webUrl"),
                        "embed_url": report.get("embedUrl"),
                        "dataset_id": report.get("datasetId"),
                        "created_datetime": report.get("createdDateTime"),
                        "modified_datetime": report.get("modifiedDateTime"),
                        "created_by": report.get("createdBy"),
                        "modified_by": report.get("modifiedBy"),
                        "report_type": report.get("reportType"),
                        "description": report.get("description", "")
                    })
                
                logger.info(
                    f"Retrieved {len(reports)} Power BI reports",
                    **add_powerbi_context(
                        workspace_id=workspace_id or "default"
                    )
                )
                
                return reports
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            logger.error(
                f"Failed to get Power BI reports: {e}",
                **add_powerbi_context(
                    workspace_id=workspace_id or "default"
                )
            )
            raise
    
    async def get_datasets(self, workspace_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of datasets from Power BI."""
        try:
            if not await self.authenticate():
                raise Exception("Authentication failed")
            
            # Use default workspace if not specified
            if workspace_id:
                url = f"{self.api_url}v1.0/myorg/groups/{workspace_id}/datasets"
            else:
                url = f"{self.api_url}v1.0/myorg/datasets"
            
            response = await self.http_client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                datasets = []
                
                for dataset in data.get("value", []):
                    datasets.append({
                        "id": dataset.get("id"),
                        "name": dataset.get("name"),
                        "web_url": dataset.get("webUrl"),
                        "add_rows_api_enabled": dataset.get("addRowsAPIEnabled", False),
                        "configured_by": dataset.get("configuredBy"),
                        "is_refreshable": dataset.get("isRefreshable", False),
                        "is_effective_identity_required": dataset.get("isEffectiveIdentityRequired", False),
                        "is_effective_identity_roles_required": dataset.get("isEffectiveIdentityRolesRequired", False),
                        "is_on_prem_gateway_required": dataset.get("isOnPremGatewayRequired", False),
                        "target_storage_mode": dataset.get("targetStorageMode"),
                        "created_date": dataset.get("createdDate"),
                        "created_by": dataset.get("createdBy"),
                        "modified_date": dataset.get("modifiedDate"),
                        "modified_by": dataset.get("modifiedBy"),
                        "description": dataset.get("description", "")
                    })
                
                logger.info(
                    f"Retrieved {len(datasets)} Power BI datasets",
                    **add_powerbi_context(
                        workspace_id=workspace_id or "default"
                    )
                )
                
                return datasets
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            logger.error(
                f"Failed to get Power BI datasets: {e}",
                **add_powerbi_context(
                    workspace_id=workspace_id or "default"
                )
            )
            raise
    
    async def refresh_dataset(
        self,
        dataset_id: str,
        workspace_id: Optional[str] = None,
        notify_option: str = "MailOnFailure"
    ) -> Dict[str, Any]:
        """Refresh a Power BI dataset."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            if not await self.authenticate():
                raise Exception("Authentication failed")
            
            # Use default workspace if not specified
            if workspace_id:
                url = f"{self.api_url}v1.0/myorg/groups/{workspace_id}/datasets/{dataset_id}/refreshes"
            else:
                url = f"{self.api_url}v1.0/myorg/datasets/{dataset_id}/refreshes"
            
            # Prepare refresh request
            refresh_request = {
                "notifyOption": notify_option
            }
            
            response = await self.http_client.post(url, json=refresh_request)
            
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            
            if response.status_code == 202:
                # Refresh initiated successfully
                request_id = response.headers.get("RequestId")
                
                result = {
                    "success": True,
                    "request_id": request_id,
                    "dataset_id": dataset_id,
                    "workspace_id": workspace_id,
                    "notify_option": notify_option,
                    "refresh_time_ms": duration_ms
                }
                
                logger.info(
                    f"Dataset refresh initiated: {dataset_id}",
                    **add_performance_context(
                        operation="refresh_dataset",
                        duration_ms=duration_ms
                    ),
                    **add_powerbi_context(
                        workspace_id=workspace_id or "default",
                        dataset_id=dataset_id
                    )
                )
                
                return result
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            
            logger.error(
                f"Failed to refresh dataset {dataset_id}: {e}",
                **add_performance_context(
                    operation="refresh_dataset",
                    duration_ms=duration_ms,
                    success=False,
                    error_type=type(e).__name__
                ),
                **add_powerbi_context(
                    workspace_id=workspace_id or "default",
                    dataset_id=dataset_id
                )
            )
            
            return {
                "success": False,
                "error": str(e),
                "refresh_time_ms": duration_ms
            }
    
    async def get_refresh_history(
        self,
        dataset_id: str,
        workspace_id: Optional[str] = None,
        top: int = 10
    ) -> List[Dict[str, Any]]:
        """Get refresh history for a dataset."""
        try:
            if not await self.authenticate():
                raise Exception("Authentication failed")
            
            # Use default workspace if not specified
            if workspace_id:
                url = f"{self.api_url}v1.0/myorg/groups/{workspace_id}/datasets/{dataset_id}/refreshes"
            else:
                url = f"{self.api_url}v1.0/myorg/datasets/{dataset_id}/refreshes"
            
            # Add query parameters
            params = {"$top": top}
            
            response = await self.http_client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                refreshes = []
                
                for refresh in data.get("value", []):
                    refreshes.append({
                        "id": refresh.get("id"),
                        "request_id": refresh.get("requestId"),
                        "refresh_type": refresh.get("refreshType"),
                        "start_time": refresh.get("startTime"),
                        "end_time": refresh.get("endTime"),
                        "status": refresh.get("status"),
                        "service_exception_json": refresh.get("serviceExceptionJson"),
                        "error": refresh.get("error"),
                        "percent_complete": refresh.get("percentComplete"),
                        "objects": refresh.get("objects", [])
                    })
                
                logger.info(
                    f"Retrieved {len(refreshes)} refresh records for dataset {dataset_id}",
                    **add_powerbi_context(
                        workspace_id=workspace_id or "default",
                        dataset_id=dataset_id
                    )
                )
                
                return refreshes
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            logger.error(
                f"Failed to get refresh history for dataset {dataset_id}: {e}",
                **add_powerbi_context(
                    workspace_id=workspace_id or "default",
                    dataset_id=dataset_id
                )
            )
            raise
    
    async def export_report(
        self,
        report_id: str,
        workspace_id: Optional[str] = None,
        file_format: str = "PDF",
        power_bi_report_configuration: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Export a Power BI report."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            if not await self.authenticate():
                raise Exception("Authentication failed")
            
            # Use default workspace if not specified
            if workspace_id:
                url = f"{self.api_url}v1.0/myorg/groups/{workspace_id}/reports/{report_id}/ExportTo"
            else:
                url = f"{self.api_url}v1.0/myorg/reports/{report_id}/ExportTo"
            
            # Prepare export request
            export_request = {
                "format": file_format
            }
            
            if power_bi_report_configuration:
                export_request["powerBIReportConfiguration"] = power_bi_report_configuration
            
            response = await self.http_client.post(url, json=export_request)
            
            if response.status_code == 202:
                # Export initiated successfully
                export_id = response.json().get("id")
                
                result = {
                    "success": True,
                    "export_id": export_id,
                    "report_id": report_id,
                    "workspace_id": workspace_id,
                    "format": file_format,
                    "status": "InProgress"
                }
                
                duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
                
                logger.info(
                    f"Report export initiated: {report_id}",
                    **add_performance_context(
                        operation="export_report",
                        duration_ms=duration_ms
                    ),
                    **add_powerbi_context(
                        workspace_id=workspace_id or "default",
                        report_id=report_id
                    )
                )
                
                return result
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            
            logger.error(
                f"Failed to export report {report_id}: {e}",
                **add_performance_context(
                    operation="export_report",
                    duration_ms=duration_ms,
                    success=False,
                    error_type=type(e).__name__
                ),
                **add_powerbi_context(
                    workspace_id=workspace_id or "default",
                    report_id=report_id
                )
            )
            
            return {
                "success": False,
                "error": str(e),
                "export_time_ms": duration_ms
            }
    
    async def close_connection(self):
        """Close connection to Power BI."""
        try:
            if self.http_client:
                await self.http_client.aclose()
                
            self._token = None
            self._token_expires_at = None
            
            logger.info(
                "Power BI connection closed",
                **add_powerbi_context(
                    workspace_id="system"
                )
            )
            
        except Exception as e:
            logger.warning(
                f"Error closing Power BI connection: {e}",
                **add_powerbi_context(
                    workspace_id="system"
                )
            )
    
    def __del__(self):
        """Cleanup on deletion."""
        if hasattr(self, 'http_client') and self.http_client:
            # Can't use async in __del__, so this is best effort
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.http_client.aclose())
            except:
                pass