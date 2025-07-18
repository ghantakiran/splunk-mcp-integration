"""
Jira integration manager for ITSM Service.
"""

import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from jira import JIRA
from atlassian import Jira as AtlassianJira

from ..core.logging import get_logger, add_itsm_context, add_performance_context
from ..models.itsm_models import ITSMTicket, ITSMIntegration, TicketStatus, TicketPriority

logger = get_logger(__name__)


class JiraManager:
    """Manages Jira integration operations."""
    
    def __init__(self, integration: ITSMIntegration):
        self.integration = integration
        self.client = None
        self.atlassian_client = None
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize Jira client."""
        try:
            credentials = self.integration.credentials
            
            # Initialize Jira Python client
            if credentials.get("token"):
                # Use token authentication
                self.client = JIRA(
                    server=self.integration.endpoint_url,
                    token_auth=credentials.get("token")
                )
            else:
                # Use username/password authentication
                self.client = JIRA(
                    server=self.integration.endpoint_url,
                    basic_auth=(
                        credentials.get("username"),
                        credentials.get("password")
                    )
                )
            
            # Initialize Atlassian Python API client for advanced operations
            if credentials.get("token"):
                self.atlassian_client = AtlassianJira(
                    url=self.integration.endpoint_url,
                    token=credentials.get("token")
                )
            else:
                self.atlassian_client = AtlassianJira(
                    url=self.integration.endpoint_url,
                    username=credentials.get("username"),
                    password=credentials.get("password")
                )
            
            logger.info(
                "Jira client initialized",
                **add_itsm_context("jira", "init", "client_init")
            )
        except Exception as e:
            logger.error(
                "Failed to initialize Jira client",
                error=str(e),
                **add_itsm_context("jira", "init", "client_init")
            )
            raise
    
    async def test_connection(self) -> Tuple[bool, str]:
        """Test Jira connection."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            
            def _test():
                # Test by getting user info
                user = self.client.myself()
                return user is not None
            
            result = await loop.run_in_executor(None, _test)
            
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            
            if result:
                logger.info(
                    "Jira connection test successful",
                    **add_performance_context("connection_test", duration_ms),
                    **add_itsm_context("jira", "test", "connection_test")
                )
                return True, "Connection successful"
            else:
                logger.error(
                    "Jira connection test failed",
                    **add_performance_context("connection_test", duration_ms, False),
                    **add_itsm_context("jira", "test", "connection_test")
                )
                return False, "Connection failed"
                
        except Exception as e:
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            error_msg = f"Connection test error: {str(e)}"
            
            logger.error(
                "Jira connection test error",
                error=error_msg,
                **add_performance_context("connection_test", duration_ms, False, "connection_error"),
                **add_itsm_context("jira", "test", "connection_test")
            )
            return False, error_msg
    
    async def create_ticket(
        self,
        ticket_data: Dict[str, Any],
        user_id: str,
        project_key: str,
        issue_type: str = "Task"
    ) -> Dict[str, Any]:
        """Create a ticket in Jira."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            loop = asyncio.get_event_loop()
            
            def _create():
                # Map fields to Jira format
                jira_data = self._map_to_jira(ticket_data, project_key, issue_type)
                
                issue = self.client.create_issue(fields=jira_data)
                return issue
            
            result = await loop.run_in_executor(None, _create)
            
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            
            logger.info(
                "Jira ticket created successfully",
                ticket_id=result.key,
                **add_performance_context("create_ticket", duration_ms),
                **add_itsm_context("jira", result.key, "create", issue_type)
            )
            
            return {
                "id": result.id,
                "key": result.key,
                "summary": result.fields.summary,
                "description": getattr(result.fields, 'description', None),
                "status": result.fields.status.name,
                "priority": getattr(result.fields.priority, 'name', None),
                "assignee": getattr(result.fields.assignee, 'displayName', None) if result.fields.assignee else None,
                "reporter": result.fields.reporter.displayName if result.fields.reporter else None,
                "created": result.fields.created,
                "updated": result.fields.updated,
                "project": result.fields.project.key,
                "issue_type": result.fields.issuetype.name,
                "raw_data": result.raw
            }
            
        except Exception as e:
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            
            logger.error(
                "Jira ticket creation failed",
                error=str(e),
                **add_performance_context("create_ticket", duration_ms, False, "creation_error"),
                **add_itsm_context("jira", "unknown", "create", issue_type)
            )
            raise
    
    async def update_ticket(
        self,
        ticket_id: str,
        ticket_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update a ticket in Jira."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            loop = asyncio.get_event_loop()
            
            def _update():
                issue = self.client.issue(ticket_id)
                
                # Map fields to Jira format
                jira_data = self._map_to_jira_update(ticket_data)
                
                # Update issue
                issue.update(fields=jira_data)
                
                # Refresh issue to get updated data
                issue = self.client.issue(ticket_id)
                return issue
            
            result = await loop.run_in_executor(None, _update)
            
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            
            logger.info(
                "Jira ticket updated successfully",
                **add_performance_context("update_ticket", duration_ms),
                **add_itsm_context("jira", ticket_id, "update", result.fields.issuetype.name)
            )
            
            return {
                "id": result.id,
                "key": result.key,
                "summary": result.fields.summary,
                "description": getattr(result.fields, 'description', None),
                "status": result.fields.status.name,
                "priority": getattr(result.fields.priority, 'name', None),
                "assignee": getattr(result.fields.assignee, 'displayName', None) if result.fields.assignee else None,
                "reporter": result.fields.reporter.displayName if result.fields.reporter else None,
                "created": result.fields.created,
                "updated": result.fields.updated,
                "project": result.fields.project.key,
                "issue_type": result.fields.issuetype.name,
                "raw_data": result.raw
            }
            
        except Exception as e:
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            
            logger.error(
                "Jira ticket update failed",
                error=str(e),
                **add_performance_context("update_ticket", duration_ms, False, "update_error"),
                **add_itsm_context("jira", ticket_id, "update", "unknown")
            )
            raise
    
    async def get_ticket(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """Get a ticket from Jira."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            loop = asyncio.get_event_loop()
            
            def _get():
                try:
                    issue = self.client.issue(ticket_id)
                    return issue
                except Exception:
                    return None
            
            result = await loop.run_in_executor(None, _get)
            
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            
            if result:
                logger.info(
                    "Jira ticket retrieved successfully",
                    **add_performance_context("get_ticket", duration_ms),
                    **add_itsm_context("jira", ticket_id, "get", result.fields.issuetype.name)
                )
                
                return {
                    "id": result.id,
                    "key": result.key,
                    "summary": result.fields.summary,
                    "description": getattr(result.fields, 'description', None),
                    "status": result.fields.status.name,
                    "priority": getattr(result.fields.priority, 'name', None),
                    "assignee": getattr(result.fields.assignee, 'displayName', None) if result.fields.assignee else None,
                    "reporter": result.fields.reporter.displayName if result.fields.reporter else None,
                    "created": result.fields.created,
                    "updated": result.fields.updated,
                    "project": result.fields.project.key,
                    "issue_type": result.fields.issuetype.name,
                    "raw_data": result.raw
                }
            else:
                logger.warning(
                    "Jira ticket not found",
                    **add_performance_context("get_ticket", duration_ms, False, "not_found"),
                    **add_itsm_context("jira", ticket_id, "get", "unknown")
                )
                return None
                
        except Exception as e:
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            
            logger.error(
                "Jira ticket retrieval failed",
                error=str(e),
                **add_performance_context("get_ticket", duration_ms, False, "retrieval_error"),
                **add_itsm_context("jira", ticket_id, "get", "unknown")
            )
            raise
    
    async def search_tickets(
        self,
        query: Dict[str, Any],
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Search tickets in Jira."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            loop = asyncio.get_event_loop()
            
            def _search():
                # Build JQL query
                jql_query = self._build_jql_query(query)
                
                issues = self.client.search_issues(
                    jql_query,
                    startAt=offset,
                    maxResults=limit
                )
                return issues
            
            results = await loop.run_in_executor(None, _search)
            
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            
            logger.info(
                "Jira ticket search completed",
                count=len(results),
                **add_performance_context("search_tickets", duration_ms),
                **add_itsm_context("jira", "search", "search", "query")
            )
            
            return [
                {
                    "id": issue.id,
                    "key": issue.key,
                    "summary": issue.fields.summary,
                    "description": getattr(issue.fields, 'description', None),
                    "status": issue.fields.status.name,
                    "priority": getattr(issue.fields.priority, 'name', None),
                    "assignee": getattr(issue.fields.assignee, 'displayName', None) if issue.fields.assignee else None,
                    "reporter": issue.fields.reporter.displayName if issue.fields.reporter else None,
                    "created": issue.fields.created,
                    "updated": issue.fields.updated,
                    "project": issue.fields.project.key,
                    "issue_type": issue.fields.issuetype.name,
                    "raw_data": issue.raw
                }
                for issue in results
            ]
            
        except Exception as e:
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            
            logger.error(
                "Jira ticket search failed",
                error=str(e),
                **add_performance_context("search_tickets", duration_ms, False, "search_error"),
                **add_itsm_context("jira", "search", "search", "query")
            )
            raise
    
    def _map_to_jira(
        self,
        ticket_data: Dict[str, Any],
        project_key: str,
        issue_type: str
    ) -> Dict[str, Any]:
        """Map generic ticket data to Jira format."""
        field_mappings = self.integration.field_mappings.get("issue", {})
        
        jira_data = {
            "project": {"key": project_key},
            "issuetype": {"name": issue_type}
        }
        
        # Standard mappings
        if "title" in ticket_data:
            jira_data["summary"] = ticket_data["title"]
        
        if "description" in ticket_data:
            jira_data["description"] = ticket_data["description"]
        
        # Priority mapping
        if "priority" in ticket_data:
            priority_map = {
                "emergency": "Highest",
                "critical": "High",
                "high": "High", 
                "medium": "Medium",
                "low": "Low"
            }
            jira_priority = priority_map.get(ticket_data["priority"].lower(), "Medium")
            jira_data["priority"] = {"name": jira_priority}
        
        # Assignee mapping
        if "assigned_to" in ticket_data:
            jira_data["assignee"] = {"name": ticket_data["assigned_to"]}
        
        # Due date mapping
        if "due_date" in ticket_data:
            jira_data["duedate"] = ticket_data["due_date"]
        
        # Custom fields
        if "custom_fields" in ticket_data:
            for field_id, value in ticket_data["custom_fields"].items():
                # Check for custom field mapping
                mapped_field = field_mappings.get(field_id, field_id)
                jira_data[mapped_field] = value
        
        return jira_data
    
    def _map_to_jira_update(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map generic ticket data to Jira update format."""
        jira_data = {}
        
        # Standard mappings for updates
        if "title" in ticket_data:
            jira_data["summary"] = ticket_data["title"]
        
        if "description" in ticket_data:
            jira_data["description"] = ticket_data["description"]
        
        # Priority mapping
        if "priority" in ticket_data:
            priority_map = {
                "emergency": "Highest",
                "critical": "High",
                "high": "High",
                "medium": "Medium", 
                "low": "Low"
            }
            jira_priority = priority_map.get(ticket_data["priority"].lower(), "Medium")
            jira_data["priority"] = {"name": jira_priority}
        
        # Assignee mapping
        if "assigned_to" in ticket_data:
            jira_data["assignee"] = {"name": ticket_data["assigned_to"]}
        
        # Due date mapping
        if "due_date" in ticket_data:
            jira_data["duedate"] = ticket_data["due_date"]
        
        # Custom fields
        if "custom_fields" in ticket_data:
            jira_data.update(ticket_data["custom_fields"])
        
        return jira_data
    
    def _build_jql_query(self, query: Dict[str, Any]) -> str:
        """Build JQL query from generic query."""
        jql_parts = []
        
        # Text search
        if "search" in query:
            jql_parts.append(f'text ~ "{query["search"]}"')
        
        # Status filter
        if "status" in query:
            jql_parts.append(f'status = "{query["status"]}"')
        
        # Priority filter
        if "priority" in query:
            priority_map = {
                "emergency": "Highest",
                "critical": "High", 
                "high": "High",
                "medium": "Medium",
                "low": "Low"
            }
            jira_priority = priority_map.get(query["priority"].lower())
            if jira_priority:
                jql_parts.append(f'priority = "{jira_priority}"')
        
        # Project filter
        if "project" in query:
            jql_parts.append(f'project = "{query["project"]}"')
        
        # Issue type filter
        if "issue_type" in query:
            jql_parts.append(f'issuetype = "{query["issue_type"]}"')
        
        # Date range filter
        if "created_after" in query:
            jql_parts.append(f'created >= "{query["created_after"]}"')
        
        if "created_before" in query:
            jql_parts.append(f'created <= "{query["created_before"]}"')
        
        # Assignment filter
        if "assigned_to" in query:
            jql_parts.append(f'assignee = "{query["assigned_to"]}"')
        
        if "reporter" in query:
            jql_parts.append(f'reporter = "{query["reporter"]}"')
        
        # Combine all parts with AND
        jql_query = " AND ".join(jql_parts) if jql_parts else "ORDER BY created DESC"
        
        return jql_query
    
    async def get_projects(self) -> List[Dict[str, Any]]:
        """Get available projects from Jira."""
        try:
            loop = asyncio.get_event_loop()
            
            def _get_projects():
                projects = self.client.projects()
                return projects
            
            result = await loop.run_in_executor(None, _get_projects)
            
            logger.info(
                "Jira projects retrieved",
                count=len(result),
                **add_itsm_context("jira", "projects", "get_projects")
            )
            
            return [
                {
                    "id": project.id,
                    "key": project.key,
                    "name": project.name,
                    "description": getattr(project, 'description', ''),
                    "project_type": getattr(project, 'projectTypeKey', ''),
                    "lead": getattr(project.lead, 'displayName', '') if hasattr(project, 'lead') and project.lead else ''
                }
                for project in result
            ]
            
        except Exception as e:
            logger.error(
                "Jira project retrieval failed",
                error=str(e),
                **add_itsm_context("jira", "projects", "get_projects")
            )
            raise
    
    async def get_issue_types(self, project_key: str = None) -> List[Dict[str, Any]]:
        """Get available issue types from Jira."""
        try:
            loop = asyncio.get_event_loop()
            
            def _get_issue_types():
                if project_key:
                    project = self.client.project(project_key)
                    return project.issueTypes
                else:
                    return self.client.issue_types()
            
            result = await loop.run_in_executor(None, _get_issue_types)
            
            logger.info(
                "Jira issue types retrieved",
                count=len(result),
                project=project_key,
                **add_itsm_context("jira", "issue_types", "get_issue_types")
            )
            
            return [
                {
                    "id": issue_type.id,
                    "name": issue_type.name,
                    "description": getattr(issue_type, 'description', ''),
                    "subtask": getattr(issue_type, 'subtask', False)
                }
                for issue_type in result
            ]
            
        except Exception as e:
            logger.error(
                "Jira issue type retrieval failed",
                error=str(e),
                project=project_key,
                **add_itsm_context("jira", "issue_types", "get_issue_types")
            )
            raise