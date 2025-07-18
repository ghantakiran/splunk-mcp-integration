"""
Tableau Server integration manager.
"""

import asyncio
from typing import Dict, List, Optional, Any, Union
import tableauserverclient as TSC
import tempfile
import os
from pathlib import Path

from ..core.config import settings
from ..core.logging import get_logger, add_tableau_context, add_performance_context
from ..models.bi_models import BIIntegration, BIWorkbook, BIDataSource, PublishStatus

logger = get_logger(__name__)


class TableauManager:
    """Tableau Server integration manager."""
    
    def __init__(self, integration: BIIntegration):
        self.integration = integration
        self.server = None
        self._authenticated = False
        
        # Initialize Tableau Server connection
        self.server_url = integration.server_url
        self.site_id = integration.site_id or ""
        self.credentials = integration.credentials
        
        # Create server instance
        self.server = TSC.Server(self.server_url)
        
        # Configure authentication
        if "token_name" in self.credentials and "token_value" in self.credentials:
            self.auth = TSC.PersonalAccessTokenAuth(
                self.credentials["token_name"],
                self.credentials["token_value"],
                self.site_id
            )
        elif "username" in self.credentials and "password" in self.credentials:
            self.auth = TSC.TableauAuth(
                self.credentials["username"],
                self.credentials["password"],
                self.site_id
            )
        else:
            raise ValueError("Invalid Tableau credentials provided")
    
    async def authenticate(self) -> bool:
        """Authenticate with Tableau Server."""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.server.auth.sign_in, self.auth)
            self._authenticated = True
            
            logger.info(
                "Tableau authentication successful",
                **add_tableau_context(
                    site_id=self.site_id
                )
            )
            
            return True
            
        except Exception as e:
            logger.error(
                f"Tableau authentication failed: {e}",
                **add_tableau_context(
                    site_id=self.site_id
                )
            )
            return False
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to Tableau Server."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            if not self._authenticated:
                auth_success = await self.authenticate()
                if not auth_success:
                    return {
                        "success": False,
                        "error": "Authentication failed",
                        "details": "Could not authenticate with Tableau Server"
                    }
            
            # Test by getting server info
            loop = asyncio.get_event_loop()
            server_info = await loop.run_in_executor(None, self.server.server_info.get)
            
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            
            logger.info(
                "Tableau connection test successful",
                **add_performance_context(
                    operation="connection_test",
                    duration_ms=duration_ms
                ),
                **add_tableau_context(
                    site_id=self.site_id
                )
            )
            
            return {
                "success": True,
                "server_info": {
                    "product_version": server_info.product_version,
                    "build_number": server_info.build_number,
                    "supported_versions": server_info.supported_versions
                },
                "response_time_ms": duration_ms
            }
            
        except Exception as e:
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            
            logger.error(
                f"Tableau connection test failed: {e}",
                **add_performance_context(
                    operation="connection_test",
                    duration_ms=duration_ms,
                    success=False,
                    error_type=type(e).__name__
                ),
                **add_tableau_context(
                    site_id=self.site_id
                )
            )
            
            return {
                "success": False,
                "error": str(e),
                "response_time_ms": duration_ms
            }
    
    async def get_projects(self) -> List[Dict[str, Any]]:
        """Get list of projects from Tableau Server."""
        try:
            if not self._authenticated:
                await self.authenticate()
            
            loop = asyncio.get_event_loop()
            all_projects, _ = await loop.run_in_executor(
                None, self.server.projects.get
            )
            
            projects = []
            for project in all_projects:
                projects.append({
                    "id": project.id,
                    "name": project.name,
                    "description": project.description,
                    "content_permissions": project.content_permissions,
                    "parent_id": project.parent_id
                })
            
            logger.info(
                f"Retrieved {len(projects)} Tableau projects",
                **add_tableau_context(
                    site_id=self.site_id
                )
            )
            
            return projects
            
        except Exception as e:
            logger.error(
                f"Failed to get Tableau projects: {e}",
                **add_tableau_context(
                    site_id=self.site_id
                )
            )
            raise
    
    async def get_workbooks(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of workbooks from Tableau Server."""
        try:
            if not self._authenticated:
                await self.authenticate()
            
            loop = asyncio.get_event_loop()
            
            # Set up request options
            req_option = TSC.RequestOptions()
            if project_id:
                req_option.filter.add(TSC.Filter(TSC.RequestOptions.Field.ProjectId,
                                                TSC.RequestOptions.Operator.Equals,
                                                project_id))
            
            all_workbooks, _ = await loop.run_in_executor(
                None, self.server.workbooks.get, req_option
            )
            
            workbooks = []
            for workbook in all_workbooks:
                workbooks.append({
                    "id": workbook.id,
                    "name": workbook.name,
                    "description": getattr(workbook, "description", ""),
                    "project_id": workbook.project_id,
                    "project_name": workbook.project_name,
                    "owner_id": workbook.owner_id,
                    "created_at": workbook.created_at,
                    "updated_at": workbook.updated_at,
                    "size": workbook.size,
                    "webpage_url": workbook.webpage_url,
                    "show_tabs": workbook.show_tabs,
                    "tags": [tag.label for tag in workbook.tags] if workbook.tags else []
                })
            
            logger.info(
                f"Retrieved {len(workbooks)} Tableau workbooks",
                **add_tableau_context(
                    site_id=self.site_id,
                    project_id=project_id
                )
            )
            
            return workbooks
            
        except Exception as e:
            logger.error(
                f"Failed to get Tableau workbooks: {e}",
                **add_tableau_context(
                    site_id=self.site_id,
                    project_id=project_id
                )
            )
            raise
    
    async def get_data_sources(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of data sources from Tableau Server."""
        try:
            if not self._authenticated:
                await self.authenticate()
            
            loop = asyncio.get_event_loop()
            
            # Set up request options
            req_option = TSC.RequestOptions()
            if project_id:
                req_option.filter.add(TSC.Filter(TSC.RequestOptions.Field.ProjectId,
                                                TSC.RequestOptions.Operator.Equals,
                                                project_id))
            
            all_datasources, _ = await loop.run_in_executor(
                None, self.server.datasources.get, req_option
            )
            
            data_sources = []
            for datasource in all_datasources:
                data_sources.append({
                    "id": datasource.id,
                    "name": datasource.name,
                    "description": getattr(datasource, "description", ""),
                    "project_id": datasource.project_id,
                    "project_name": datasource.project_name,
                    "owner_id": datasource.owner_id,
                    "created_at": datasource.created_at,
                    "updated_at": datasource.updated_at,
                    "type": datasource.datasource_type,
                    "webpage_url": datasource.webpage_url,
                    "content_url": datasource.content_url,
                    "tags": [tag.label for tag in datasource.tags] if datasource.tags else []
                })
            
            logger.info(
                f"Retrieved {len(data_sources)} Tableau data sources",
                **add_tableau_context(
                    site_id=self.site_id,
                    project_id=project_id
                )
            )
            
            return data_sources
            
        except Exception as e:
            logger.error(
                f"Failed to get Tableau data sources: {e}",
                **add_tableau_context(
                    site_id=self.site_id,
                    project_id=project_id
                )
            )
            raise
    
    async def publish_workbook(
        self,
        file_path: str,
        project_id: str,
        workbook_name: str,
        description: Optional[str] = None,
        show_tabs: bool = True,
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """Publish workbook to Tableau Server."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            if not self._authenticated:
                await self.authenticate()
            
            # Create workbook item
            new_workbook = TSC.WorkbookItem(workbook_name, project_id=project_id)
            new_workbook.description = description or ""
            new_workbook.show_tabs = show_tabs
            
            # Set publish mode
            publish_mode = TSC.Server.PublishMode.Overwrite if overwrite else TSC.Server.PublishMode.CreateNew
            
            loop = asyncio.get_event_loop()
            published_workbook = await loop.run_in_executor(
                None,
                self.server.workbooks.publish,
                new_workbook,
                file_path,
                publish_mode
            )
            
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            
            result = {
                "success": True,
                "workbook_id": published_workbook.id,
                "name": published_workbook.name,
                "project_id": published_workbook.project_id,
                "webpage_url": published_workbook.webpage_url,
                "created_at": published_workbook.created_at,
                "size": published_workbook.size,
                "publish_time_ms": duration_ms
            }
            
            logger.info(
                f"Workbook '{workbook_name}' published successfully",
                **add_performance_context(
                    operation="publish_workbook",
                    duration_ms=duration_ms
                ),
                **add_tableau_context(
                    site_id=self.site_id,
                    workbook_id=published_workbook.id,
                    project_id=project_id
                )
            )
            
            return result
            
        except Exception as e:
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            
            logger.error(
                f"Failed to publish workbook '{workbook_name}': {e}",
                **add_performance_context(
                    operation="publish_workbook",
                    duration_ms=duration_ms,
                    success=False,
                    error_type=type(e).__name__
                ),
                **add_tableau_context(
                    site_id=self.site_id,
                    project_id=project_id
                )
            )
            
            return {
                "success": False,
                "error": str(e),
                "publish_time_ms": duration_ms
            }
    
    async def download_workbook(
        self,
        workbook_id: str,
        download_path: Optional[str] = None,
        include_extract: bool = True
    ) -> Dict[str, Any]:
        """Download workbook from Tableau Server."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            if not self._authenticated:
                await self.authenticate()
            
            # Create download path if not provided
            if not download_path:
                temp_dir = tempfile.mkdtemp()
                download_path = os.path.join(temp_dir, f"workbook_{workbook_id}.twbx")
            
            loop = asyncio.get_event_loop()
            
            # Download workbook
            file_path = await loop.run_in_executor(
                None,
                self.server.workbooks.download,
                workbook_id,
                download_path,
                include_extract
            )
            
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            file_size = os.path.getsize(file_path)
            
            result = {
                "success": True,
                "file_path": file_path,
                "file_size_bytes": file_size,
                "download_time_ms": duration_ms
            }
            
            logger.info(
                f"Workbook {workbook_id} downloaded successfully",
                **add_performance_context(
                    operation="download_workbook",
                    duration_ms=duration_ms
                ),
                **add_tableau_context(
                    site_id=self.site_id,
                    workbook_id=workbook_id
                )
            )
            
            return result
            
        except Exception as e:
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            
            logger.error(
                f"Failed to download workbook {workbook_id}: {e}",
                **add_performance_context(
                    operation="download_workbook",
                    duration_ms=duration_ms,
                    success=False,
                    error_type=type(e).__name__
                ),
                **add_tableau_context(
                    site_id=self.site_id,
                    workbook_id=workbook_id
                )
            )
            
            return {
                "success": False,
                "error": str(e),
                "download_time_ms": duration_ms
            }
    
    async def refresh_extract(
        self,
        datasource_id: str,
        extract_refresh_type: str = "FullRefresh"
    ) -> Dict[str, Any]:
        """Refresh data source extract."""
        try:
            if not self._authenticated:
                await self.authenticate()
            
            loop = asyncio.get_event_loop()
            
            # Get data source
            datasource = await loop.run_in_executor(
                None, self.server.datasources.get_by_id, datasource_id
            )
            
            # Trigger refresh
            job = await loop.run_in_executor(
                None, self.server.datasources.refresh, datasource
            )
            
            result = {
                "success": True,
                "job_id": job.id,
                "job_type": job.job_type,
                "progress": job.progress,
                "created_at": job.created_at,
                "started_at": job.started_at,
                "completed_at": job.completed_at
            }
            
            logger.info(
                f"Extract refresh started for data source {datasource_id}",
                **add_tableau_context(
                    site_id=self.site_id,
                    datasource_id=datasource_id
                )
            )
            
            return result
            
        except Exception as e:
            logger.error(
                f"Failed to refresh extract for data source {datasource_id}: {e}",
                **add_tableau_context(
                    site_id=self.site_id,
                    datasource_id=datasource_id
                )
            )
            
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get status of a background job."""
        try:
            if not self._authenticated:
                await self.authenticate()
            
            loop = asyncio.get_event_loop()
            job = await loop.run_in_executor(
                None, self.server.jobs.get_by_id, job_id
            )
            
            return {
                "id": job.id,
                "job_type": job.job_type,
                "progress": job.progress,
                "created_at": job.created_at,
                "started_at": job.started_at,
                "completed_at": job.completed_at,
                "finish_code": job.finish_code,
                "notes": [note.value for note in job.notes] if job.notes else []
            }
            
        except Exception as e:
            logger.error(
                f"Failed to get job status for {job_id}: {e}",
                **add_tableau_context(
                    site_id=self.site_id
                )
            )
            raise
    
    async def close_connection(self):
        """Close connection to Tableau Server."""
        try:
            if self._authenticated and self.server:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.server.auth.sign_out)
                self._authenticated = False
                
                logger.info(
                    "Tableau connection closed",
                    **add_tableau_context(
                        site_id=self.site_id
                    )
                )
                
        except Exception as e:
            logger.warning(
                f"Error closing Tableau connection: {e}",
                **add_tableau_context(
                    site_id=self.site_id
                )
            )
    
    def __del__(self):
        """Cleanup on deletion."""
        if hasattr(self, '_authenticated') and self._authenticated:
            # Note: Can't use async in __del__, so this is best effort
            try:
                if self.server:
                    self.server.auth.sign_out()
            except:
                pass