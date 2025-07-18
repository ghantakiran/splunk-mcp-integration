"""
ServiceNow integration manager for ITSM Service.
"""

import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import pysnow
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.logging import get_logger, add_itsm_context, add_performance_context
from ..models.itsm_models import ITSMTicket, ITSMIntegration, TicketStatus, TicketPriority

logger = get_logger(__name__)


class ServiceNowManager:
    """Manages ServiceNow integration operations."""
    
    def __init__(self, integration: ITSMIntegration):
        self.integration = integration
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize ServiceNow client."""
        try:
            credentials = self.integration.credentials
            self.client = pysnow.Client(
                instance=credentials.get("instance"),
                user=credentials.get("username"),
                password=credentials.get("password")
            )
            logger.info(
                "ServiceNow client initialized",
                **add_itsm_context("servicenow", "init", "client_init")
            )
        except Exception as e:
            logger.error(
                "Failed to initialize ServiceNow client",
                error=str(e),
                **add_itsm_context("servicenow", "init", "client_init")
            )
            raise
    
    async def test_connection(self) -> Tuple[bool, str]:
        """Test ServiceNow connection."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            
            def _test():
                # Test by getting a single record from incident table
                incident = self.client.resource(api_path='/table/incident')
                response = incident.get(query={'limit': 1})
                return response.status_code == 200
            
            result = await loop.run_in_executor(None, _test)
            
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            
            if result:
                logger.info(
                    "ServiceNow connection test successful",
                    **add_performance_context("connection_test", duration_ms),
                    **add_itsm_context("servicenow", "test", "connection_test")
                )
                return True, "Connection successful"
            else:
                logger.error(
                    "ServiceNow connection test failed",
                    **add_performance_context("connection_test", duration_ms, False),
                    **add_itsm_context("servicenow", "test", "connection_test")
                )
                return False, "Connection failed"
                
        except Exception as e:
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            error_msg = f"Connection test error: {str(e)}"
            
            logger.error(
                "ServiceNow connection test error",
                error=error_msg,
                **add_performance_context("connection_test", duration_ms, False, "connection_error"),
                **add_itsm_context("servicenow", "test", "connection_test")
            )
            return False, error_msg
    
    async def create_ticket(
        self,
        ticket_data: Dict[str, Any],
        user_id: str,
        table: str = "incident"
    ) -> Dict[str, Any]:
        """Create a ticket in ServiceNow."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            loop = asyncio.get_event_loop()
            
            def _create():
                resource = self.client.resource(api_path=f'/table/{table}')
                
                # Map fields to ServiceNow format
                servicenow_data = self._map_to_servicenow(ticket_data, table)
                
                response = resource.create(payload=servicenow_data)
                return response.one()
            
            result = await loop.run_in_executor(None, _create)
            
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            
            logger.info(
                "ServiceNow ticket created successfully",
                ticket_id=result.get("sys_id"),
                **add_performance_context("create_ticket", duration_ms),
                **add_itsm_context("servicenow", result.get("sys_id"), "create", table)
            )
            
            return {
                "sys_id": result.get("sys_id"),
                "number": result.get("number"),
                "state": result.get("state"),
                "short_description": result.get("short_description"),
                "description": result.get("description"),
                "priority": result.get("priority"),
                "assigned_to": result.get("assigned_to"),
                "assignment_group": result.get("assignment_group"),
                "created_on": result.get("sys_created_on"),
                "updated_on": result.get("sys_updated_on"),
                "raw_data": dict(result)
            }
            
        except Exception as e:
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            
            logger.error(
                "ServiceNow ticket creation failed",
                error=str(e),
                **add_performance_context("create_ticket", duration_ms, False, "creation_error"),
                **add_itsm_context("servicenow", "unknown", "create", table)
            )
            raise
    
    async def update_ticket(
        self,
        ticket_id: str,
        ticket_data: Dict[str, Any],
        table: str = "incident"
    ) -> Dict[str, Any]:
        """Update a ticket in ServiceNow."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            loop = asyncio.get_event_loop()
            
            def _update():
                resource = self.client.resource(api_path=f'/table/{table}')
                
                # Map fields to ServiceNow format
                servicenow_data = self._map_to_servicenow(ticket_data, table)
                
                response = resource.update(
                    query={'sys_id': ticket_id},
                    payload=servicenow_data
                )
                return response.one()
            
            result = await loop.run_in_executor(None, _update)
            
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            
            logger.info(
                "ServiceNow ticket updated successfully",
                **add_performance_context("update_ticket", duration_ms),
                **add_itsm_context("servicenow", ticket_id, "update", table)
            )
            
            return {
                "sys_id": result.get("sys_id"),
                "number": result.get("number"),
                "state": result.get("state"),
                "short_description": result.get("short_description"),
                "description": result.get("description"),
                "priority": result.get("priority"),
                "assigned_to": result.get("assigned_to"),
                "assignment_group": result.get("assignment_group"),
                "created_on": result.get("sys_created_on"),
                "updated_on": result.get("sys_updated_on"),
                "raw_data": dict(result)
            }
            
        except Exception as e:
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            
            logger.error(
                "ServiceNow ticket update failed",
                error=str(e),
                **add_performance_context("update_ticket", duration_ms, False, "update_error"),
                **add_itsm_context("servicenow", ticket_id, "update", table)
            )
            raise
    
    async def get_ticket(
        self,
        ticket_id: str,
        table: str = "incident"
    ) -> Optional[Dict[str, Any]]:
        """Get a ticket from ServiceNow."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            loop = asyncio.get_event_loop()
            
            def _get():
                resource = self.client.resource(api_path=f'/table/{table}')
                response = resource.get(query={'sys_id': ticket_id})
                records = list(response)
                return records[0] if records else None
            
            result = await loop.run_in_executor(None, _get)
            
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            
            if result:
                logger.info(
                    "ServiceNow ticket retrieved successfully",
                    **add_performance_context("get_ticket", duration_ms),
                    **add_itsm_context("servicenow", ticket_id, "get", table)
                )
                
                return {
                    "sys_id": result.get("sys_id"),
                    "number": result.get("number"),
                    "state": result.get("state"),
                    "short_description": result.get("short_description"),
                    "description": result.get("description"),
                    "priority": result.get("priority"),
                    "assigned_to": result.get("assigned_to"),
                    "assignment_group": result.get("assignment_group"),
                    "created_on": result.get("sys_created_on"),
                    "updated_on": result.get("sys_updated_on"),
                    "raw_data": dict(result)
                }
            else:
                logger.warning(
                    "ServiceNow ticket not found",
                    **add_performance_context("get_ticket", duration_ms, False, "not_found"),
                    **add_itsm_context("servicenow", ticket_id, "get", table)
                )
                return None
                
        except Exception as e:
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            
            logger.error(
                "ServiceNow ticket retrieval failed",
                error=str(e),
                **add_performance_context("get_ticket", duration_ms, False, "retrieval_error"),
                **add_itsm_context("servicenow", ticket_id, "get", table)
            )
            raise
    
    async def search_tickets(
        self,
        query: Dict[str, Any],
        table: str = "incident",
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Search tickets in ServiceNow."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            loop = asyncio.get_event_loop()
            
            def _search():
                resource = self.client.resource(api_path=f'/table/{table}')
                
                # Build ServiceNow query
                servicenow_query = self._build_servicenow_query(query)
                servicenow_query.update({
                    'sysparm_limit': limit,
                    'sysparm_offset': offset
                })
                
                response = resource.get(query=servicenow_query)
                return list(response)
            
            results = await loop.run_in_executor(None, _search)
            
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            
            logger.info(
                "ServiceNow ticket search completed",
                count=len(results),
                **add_performance_context("search_tickets", duration_ms),
                **add_itsm_context("servicenow", "search", "search", table)
            )
            
            return [
                {
                    "sys_id": result.get("sys_id"),
                    "number": result.get("number"),
                    "state": result.get("state"),
                    "short_description": result.get("short_description"),
                    "description": result.get("description"),
                    "priority": result.get("priority"),
                    "assigned_to": result.get("assigned_to"),
                    "assignment_group": result.get("assignment_group"),
                    "created_on": result.get("sys_created_on"),
                    "updated_on": result.get("sys_updated_on"),
                    "raw_data": dict(result)
                }
                for result in results
            ]
            
        except Exception as e:
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            
            logger.error(
                "ServiceNow ticket search failed",
                error=str(e),
                **add_performance_context("search_tickets", duration_ms, False, "search_error"),
                **add_itsm_context("servicenow", "search", "search", table)
            )
            raise
    
    def _map_to_servicenow(self, ticket_data: Dict[str, Any], table: str) -> Dict[str, Any]:
        """Map generic ticket data to ServiceNow format."""
        field_mappings = self.integration.field_mappings.get(table, {})
        
        servicenow_data = {}
        
        # Standard mappings
        standard_mappings = {
            "title": "short_description",
            "description": "description",
            "priority": "priority",
            "status": "state",
            "assigned_to": "assigned_to",
            "assigned_group": "assignment_group",
            "category": "category",
            "subcategory": "subcategory"
        }
        
        for generic_field, servicenow_field in standard_mappings.items():
            if generic_field in ticket_data:
                # Check for custom mapping
                target_field = field_mappings.get(generic_field, servicenow_field)
                servicenow_data[target_field] = ticket_data[generic_field]
        
        # Handle priority mapping
        if "priority" in ticket_data:
            priority_map = {
                "emergency": "1",
                "critical": "2", 
                "high": "3",
                "medium": "4",
                "low": "5"
            }
            servicenow_data["priority"] = priority_map.get(
                ticket_data["priority"].lower(),
                "4"  # Default to medium
            )
        
        # Handle state mapping
        if "status" in ticket_data:
            state_map = {
                "new": "1",
                "in_progress": "2",
                "pending": "4",
                "resolved": "6",
                "closed": "7",
                "cancelled": "8"
            }
            servicenow_data["state"] = state_map.get(
                ticket_data["status"].lower(),
                "1"  # Default to new
            )
        
        # Add custom fields
        if "custom_fields" in ticket_data:
            servicenow_data.update(ticket_data["custom_fields"])
        
        return servicenow_data
    
    def _build_servicenow_query(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Build ServiceNow query from generic query."""
        servicenow_query = {}
        
        # Text search
        if "search" in query:
            servicenow_query["sysparm_query"] = f"short_descriptionLIKE{query['search']}^ORdescriptionLIKE{query['search']}"
        
        # Status filter
        if "status" in query:
            state_map = {
                "new": "1",
                "in_progress": "2", 
                "pending": "4",
                "resolved": "6",
                "closed": "7",
                "cancelled": "8"
            }
            if query["status"] in state_map:
                state_query = f"state={state_map[query['status']]}"
                if "sysparm_query" in servicenow_query:
                    servicenow_query["sysparm_query"] += f"^{state_query}"
                else:
                    servicenow_query["sysparm_query"] = state_query
        
        # Priority filter
        if "priority" in query:
            priority_map = {
                "emergency": "1",
                "critical": "2",
                "high": "3", 
                "medium": "4",
                "low": "5"
            }
            if query["priority"] in priority_map:
                priority_query = f"priority={priority_map[query['priority']]}"
                if "sysparm_query" in servicenow_query:
                    servicenow_query["sysparm_query"] += f"^{priority_query}"
                else:
                    servicenow_query["sysparm_query"] = priority_query
        
        # Date range filter
        if "created_after" in query:
            date_query = f"sys_created_on>={query['created_after']}"
            if "sysparm_query" in servicenow_query:
                servicenow_query["sysparm_query"] += f"^{date_query}"
            else:
                servicenow_query["sysparm_query"] = date_query
        
        if "created_before" in query:
            date_query = f"sys_created_on<={query['created_before']}"
            if "sysparm_query" in servicenow_query:
                servicenow_query["sysparm_query"] += f"^{date_query}"
            else:
                servicenow_query["sysparm_query"] = date_query
        
        # Assignment filter
        if "assigned_to" in query:
            assigned_query = f"assigned_to={query['assigned_to']}"
            if "sysparm_query" in servicenow_query:
                servicenow_query["sysparm_query"] += f"^{assigned_query}"
            else:
                servicenow_query["sysparm_query"] = assigned_query
        
        if "assigned_group" in query:
            group_query = f"assignment_group={query['assigned_group']}"
            if "sysparm_query" in servicenow_query:
                servicenow_query["sysparm_query"] += f"^{group_query}"
            else:
                servicenow_query["sysparm_query"] = group_query
        
        return servicenow_query
    
    async def get_tables(self) -> List[Dict[str, Any]]:
        """Get available tables from ServiceNow."""
        try:
            loop = asyncio.get_event_loop()
            
            def _get_tables():
                # Get common ITSM tables
                tables = [
                    {"name": "incident", "label": "Incident", "description": "Incident Management"},
                    {"name": "problem", "label": "Problem", "description": "Problem Management"},
                    {"name": "change_request", "label": "Change Request", "description": "Change Management"},
                    {"name": "sc_request", "label": "Service Request", "description": "Service Request"},
                    {"name": "sc_req_item", "label": "Request Item", "description": "Service Request Items"},
                ]
                return tables
            
            result = await loop.run_in_executor(None, _get_tables)
            
            logger.info(
                "ServiceNow tables retrieved",
                count=len(result),
                **add_itsm_context("servicenow", "tables", "get_tables")
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "ServiceNow table retrieval failed",
                error=str(e),
                **add_itsm_context("servicenow", "tables", "get_tables")
            )
            raise