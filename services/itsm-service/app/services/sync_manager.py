"""
Synchronization manager for ITSM Service bidirectional data sync.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_

from ..core.logging import get_logger, add_sync_context, add_performance_context
from ..models.itsm_models import (
    ITSMIntegration, ITSMTicket, ITSMSyncRecord, 
    SyncStatus, TicketStatus, TicketPriority
)
from .servicenow_manager import ServiceNowManager
from .jira_manager import JiraManager

logger = get_logger(__name__)


class ConflictResolution:
    """Conflict resolution strategies."""
    AUTO_LOCAL = "auto_local"  # Local changes win
    AUTO_REMOTE = "auto_remote"  # Remote changes win
    MANUAL = "manual"  # Manual resolution required
    TIMESTAMP = "timestamp"  # Most recent change wins


class SyncDirection:
    """Synchronization directions."""
    INBOUND = "inbound"  # Remote -> Local
    OUTBOUND = "outbound"  # Local -> Remote
    BIDIRECTIONAL = "bidirectional"  # Both directions


class SyncManager:
    """Manages bidirectional synchronization between ITSM systems."""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.running_syncs: Dict[str, bool] = {}
    
    async def sync_integration(
        self,
        integration: ITSMIntegration,
        sync_type: str = "incremental",
        direction: str = SyncDirection.BIDIRECTIONAL,
        force: bool = False
    ) -> Dict[str, Any]:
        """Synchronize an ITSM integration."""
        
        sync_id = f"sync_{integration.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if not force and sync_id in self.running_syncs:
            raise ValueError(f"Sync already running for integration {integration.id}")
        
        self.running_syncs[sync_id] = True
        start_time = asyncio.get_event_loop().time()
        
        try:
            logger.info(
                "Starting ITSM integration sync",
                **add_sync_context(sync_id, direction, integration.provider.value, "running")
            )
            
            # Initialize provider manager
            if integration.provider.value == "servicenow":
                manager = ServiceNowManager(integration)
            elif integration.provider.value == "jira":
                manager = JiraManager(integration)
            else:
                raise ValueError(f"Unsupported provider: {integration.provider.value}")
            
            # Test connection first
            connection_ok, connection_msg = await manager.test_connection()
            if not connection_ok:
                raise Exception(f"Connection test failed: {connection_msg}")
            
            sync_results = {
                "sync_id": sync_id,
                "integration_id": integration.id,
                "provider": integration.provider.value,
                "direction": direction,
                "sync_type": sync_type,
                "started_at": datetime.utcnow().isoformat(),
                "inbound_results": None,
                "outbound_results": None,
                "conflicts": [],
                "errors": []
            }
            
            # Perform sync based on direction
            if direction in [SyncDirection.INBOUND, SyncDirection.BIDIRECTIONAL]:
                inbound_results = await self._sync_inbound(
                    integration,
                    manager,
                    sync_type,
                    sync_id
                )
                sync_results["inbound_results"] = inbound_results
            
            if direction in [SyncDirection.OUTBOUND, SyncDirection.BIDIRECTIONAL]:
                outbound_results = await self._sync_outbound(
                    integration,
                    manager,
                    sync_type,
                    sync_id
                )
                sync_results["outbound_results"] = outbound_results
            
            # Update integration sync status
            await self._update_integration_sync_status(integration, True)
            
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            sync_results["completed_at"] = datetime.utcnow().isoformat()
            sync_results["duration_ms"] = duration_ms
            
            logger.info(
                "ITSM integration sync completed",
                **add_performance_context("integration_sync", duration_ms),
                **add_sync_context(sync_id, direction, integration.provider.value, "completed")
            )
            
            return sync_results
            
        except Exception as e:
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            error_msg = str(e)
            
            # Update integration sync status with error
            await self._update_integration_sync_status(integration, False, error_msg)
            
            logger.error(
                "ITSM integration sync failed",
                error=error_msg,
                **add_performance_context("integration_sync", duration_ms, False, "sync_error"),
                **add_sync_context(sync_id, direction, integration.provider.value, "failed")
            )
            
            raise
        
        finally:
            if sync_id in self.running_syncs:
                del self.running_syncs[sync_id]
    
    async def _sync_inbound(
        self,
        integration: ITSMIntegration,
        manager: Any,
        sync_type: str,
        sync_id: str
    ) -> Dict[str, Any]:
        """Sync data from remote system to local database."""
        
        results = {
            "direction": "inbound",
            "processed": 0,
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0,
            "conflicts": 0
        }
        
        try:
            # Get available tables/projects
            if integration.provider.value == "servicenow":
                tables = await manager.get_tables()
                table_names = [table["name"] for table in tables]
            else:  # jira
                projects = await manager.get_projects()
                table_names = [project["key"] for project in projects]
            
            for table_name in table_names:
                # Skip if not in table mappings (if configured)
                if integration.table_mappings and table_name not in integration.table_mappings:
                    continue
                
                table_results = await self._sync_table_inbound(
                    integration,
                    manager,
                    table_name,
                    sync_type,
                    sync_id
                )
                
                # Aggregate results
                for key in ["processed", "created", "updated", "skipped", "errors", "conflicts"]:
                    results[key] += table_results.get(key, 0)
            
            logger.info(
                "Inbound sync completed",
                **results,
                **add_sync_context(sync_id, "inbound", integration.provider.value, "completed", results["processed"])
            )
            
        except Exception as e:
            logger.error(
                "Inbound sync failed",
                error=str(e),
                **add_sync_context(sync_id, "inbound", integration.provider.value, "failed")
            )
            raise
        
        return results
    
    async def _sync_table_inbound(
        self,
        integration: ITSMIntegration,
        manager: Any,
        table_name: str,
        sync_type: str,
        sync_id: str
    ) -> Dict[str, Any]:
        """Sync a specific table/project from remote to local."""
        
        results = {
            "table": table_name,
            "processed": 0,
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0,
            "conflicts": 0
        }
        
        try:
            # Build query based on sync type
            query = {}
            if sync_type == "incremental" and integration.last_sync_at:
                # Only get records updated since last sync
                query["updated_after"] = integration.last_sync_at.isoformat()
            
            # Get remote tickets
            if integration.provider.value == "servicenow":
                remote_tickets = await manager.search_tickets(
                    query,
                    table_name,
                    limit=1000  # Process in batches
                )
            else:  # jira
                # For Jira, table_name is project_key
                query["project"] = table_name
                remote_tickets = await manager.search_tickets(
                    query,
                    limit=1000
                )
            
            for remote_ticket in remote_tickets:
                results["processed"] += 1
                
                try:
                    result = await self._process_remote_ticket(
                        integration,
                        remote_ticket,
                        table_name,
                        sync_id
                    )
                    results[result] += 1
                    
                except Exception as e:
                    results["errors"] += 1
                    logger.error(
                        "Failed to process remote ticket",
                        error=str(e),
                        ticket_id=remote_ticket.get("id") or remote_ticket.get("sys_id"),
                        **add_sync_context(sync_id, "inbound", integration.provider.value, "error")
                    )
        
        except Exception as e:
            logger.error(
                "Table sync failed",
                error=str(e),
                table=table_name,
                **add_sync_context(sync_id, "inbound", integration.provider.value, "failed")
            )
            raise
        
        return results
    
    async def _process_remote_ticket(
        self,
        integration: ITSMIntegration,
        remote_ticket: Dict[str, Any],
        table_name: str,
        sync_id: str
    ) -> str:
        """Process a single remote ticket."""
        
        external_id = remote_ticket.get("id") or remote_ticket.get("sys_id") or remote_ticket.get("key")
        
        # Check if ticket already exists locally
        stmt = select(ITSMTicket).where(
            and_(
                ITSMTicket.integration_id == integration.id,
                ITSMTicket.external_id == external_id,
                ITSMTicket.external_table == table_name
            )
        )
        result = await self.db_session.execute(stmt)
        existing_ticket = result.scalar_one_or_none()
        
        if existing_ticket:
            # Check for conflicts
            has_conflict = await self._check_for_conflicts(
                existing_ticket,
                remote_ticket,
                integration
            )
            
            if has_conflict:
                await self._handle_conflict(
                    existing_ticket,
                    remote_ticket,
                    integration,
                    sync_id
                )
                return "conflicts"
            else:
                # Update existing ticket
                await self._update_local_ticket(
                    existing_ticket,
                    remote_ticket,
                    integration,
                    sync_id
                )
                return "updated"
        else:
            # Create new ticket
            await self._create_local_ticket(
                remote_ticket,
                integration,
                table_name,
                sync_id
            )
            return "created"
    
    async def _check_for_conflicts(
        self,
        local_ticket: ITSMTicket,
        remote_ticket: Dict[str, Any],
        integration: ITSMIntegration
    ) -> bool:
        """Check if there are conflicts between local and remote ticket."""
        
        # Check if local ticket has been modified since last sync
        if local_ticket.local_changes:
            # Get remote update time
            remote_updated = remote_ticket.get("updated_on") or remote_ticket.get("updated")
            if remote_updated:
                remote_updated_dt = datetime.fromisoformat(remote_updated.replace('Z', '+00:00'))
                
                # If both have been updated since last sync, there's a conflict
                if (local_ticket.updated_at > local_ticket.last_synced_at and 
                    remote_updated_dt > local_ticket.last_synced_at):
                    return True
        
        return False
    
    async def _handle_conflict(
        self,
        local_ticket: ITSMTicket,
        remote_ticket: Dict[str, Any],
        integration: ITSMIntegration,
        sync_id: str
    ) -> None:
        """Handle synchronization conflicts."""
        
        conflict_data = {
            "local_data": {
                "title": local_ticket.title,
                "description": local_ticket.description,
                "status": local_ticket.status.value,
                "priority": local_ticket.priority.value,
                "updated_at": local_ticket.updated_at.isoformat()
            },
            "remote_data": {
                "title": remote_ticket.get("summary") or remote_ticket.get("short_description"),
                "description": remote_ticket.get("description"),
                "status": remote_ticket.get("status") or remote_ticket.get("state"),
                "priority": remote_ticket.get("priority"),
                "updated_at": remote_ticket.get("updated_on") or remote_ticket.get("updated")
            }
        }
        
        # Store conflict for manual resolution
        local_ticket.sync_conflicts.append({
            "conflict_id": f"conflict_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            "sync_id": sync_id,
            "detected_at": datetime.utcnow().isoformat(),
            "conflict_data": conflict_data,
            "resolution_status": "pending"
        })
        
        # Create sync record
        sync_record = ITSMSyncRecord(
            integration_id=integration.id,
            ticket_id=local_ticket.id,
            sync_type="incremental",
            direction="inbound",
            status=SyncStatus.FAILED,
            external_id=local_ticket.external_id,
            external_table=local_ticket.external_table,
            operation="update",
            source_data=conflict_data["remote_data"],
            target_data=conflict_data["local_data"],
            success=False,
            error_message="Synchronization conflict detected",
            conflicts=[conflict_data],
            resolution="manual"
        )
        
        self.db_session.add(sync_record)
        await self.db_session.commit()
        
        logger.warning(
            "Synchronization conflict detected",
            ticket_id=local_ticket.id,
            external_id=local_ticket.external_id,
            **add_sync_context(sync_id, "inbound", integration.provider.value, "conflict")
        )
    
    async def _update_local_ticket(
        self,
        local_ticket: ITSMTicket,
        remote_ticket: Dict[str, Any],
        integration: ITSMIntegration,
        sync_id: str
    ) -> None:
        """Update local ticket with remote data."""
        
        # Map remote data to local fields
        mapped_data = self._map_remote_to_local(remote_ticket, integration)
        
        # Update ticket fields
        local_ticket.title = mapped_data.get("title", local_ticket.title)
        local_ticket.description = mapped_data.get("description", local_ticket.description)
        local_ticket.status = mapped_data.get("status", local_ticket.status)
        local_ticket.priority = mapped_data.get("priority", local_ticket.priority)
        local_ticket.assigned_to = mapped_data.get("assigned_to", local_ticket.assigned_to)
        local_ticket.assigned_group = mapped_data.get("assigned_group", local_ticket.assigned_group)
        
        # Update dates
        if "created_date" in mapped_data:
            local_ticket.created_date = mapped_data["created_date"]
        if "updated_date" in mapped_data:
            local_ticket.updated_date = mapped_data["updated_date"]
        if "due_date" in mapped_data:
            local_ticket.due_date = mapped_data["due_date"]
        if "resolved_date" in mapped_data:
            local_ticket.resolved_date = mapped_data["resolved_date"]
        if "closed_date" in mapped_data:
            local_ticket.closed_date = mapped_data["closed_date"]
        
        # Update external data
        local_ticket.external_data = remote_ticket
        local_ticket.last_synced_at = datetime.utcnow()
        local_ticket.sync_version = remote_ticket.get("version") or str(datetime.utcnow().timestamp())
        
        # Clear local changes since we're syncing from remote
        local_ticket.local_changes = {}
        
        # Create sync record
        sync_record = ITSMSyncRecord(
            integration_id=integration.id,
            ticket_id=local_ticket.id,
            sync_type="incremental",
            direction="inbound",
            status=SyncStatus.COMPLETED,
            external_id=local_ticket.external_id,
            external_table=local_ticket.external_table,
            operation="update",
            source_data=remote_ticket,
            target_data=mapped_data,
            success=True
        )
        
        self.db_session.add(sync_record)
        await self.db_session.commit()
    
    async def _create_local_ticket(
        self,
        remote_ticket: Dict[str, Any],
        integration: ITSMIntegration,
        table_name: str,
        sync_id: str
    ) -> None:
        """Create new local ticket from remote data."""
        
        # Map remote data to local fields
        mapped_data = self._map_remote_to_local(remote_ticket, integration)
        
        external_id = remote_ticket.get("id") or remote_ticket.get("sys_id") or remote_ticket.get("key")
        
        # Create new ticket
        local_ticket = ITSMTicket(
            integration_id=integration.id,
            external_id=external_id,
            external_table=table_name,
            title=mapped_data.get("title", ""),
            description=mapped_data.get("description"),
            status=mapped_data.get("status", TicketStatus.NEW),
            priority=mapped_data.get("priority", TicketPriority.MEDIUM),
            assigned_to=mapped_data.get("assigned_to"),
            assigned_group=mapped_data.get("assigned_group"),
            reporter=mapped_data.get("reporter"),
            created_date=mapped_data.get("created_date"),
            updated_date=mapped_data.get("updated_date"),
            due_date=mapped_data.get("due_date"),
            resolved_date=mapped_data.get("resolved_date"),
            closed_date=mapped_data.get("closed_date"),
            external_data=remote_ticket,
            last_synced_at=datetime.utcnow(),
            sync_version=remote_ticket.get("version") or str(datetime.utcnow().timestamp())
        )
        
        # Create sync record
        sync_record = ITSMSyncRecord(
            integration_id=integration.id,
            ticket_id=local_ticket.id,
            sync_type="incremental",
            direction="inbound",
            status=SyncStatus.COMPLETED,
            external_id=external_id,
            external_table=table_name,
            operation="create",
            source_data=remote_ticket,
            target_data=mapped_data,
            success=True
        )
        
        self.db_session.add(local_ticket)
        self.db_session.add(sync_record)
        await self.db_session.commit()
    
    async def _sync_outbound(
        self,
        integration: ITSMIntegration,
        manager: Any,
        sync_type: str,
        sync_id: str
    ) -> Dict[str, Any]:
        """Sync data from local database to remote system."""
        
        results = {
            "direction": "outbound",
            "processed": 0,
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0
        }
        
        try:
            # Get local tickets that need syncing
            query = select(ITSMTicket).where(
                ITSMTicket.integration_id == integration.id
            )
            
            if sync_type == "incremental":
                # Only sync tickets with local changes or never synced
                query = query.where(
                    or_(
                        ITSMTicket.local_changes != {},
                        ITSMTicket.last_synced_at.is_(None)
                    )
                )
            
            result = await self.db_session.execute(query)
            local_tickets = result.scalars().all()
            
            for local_ticket in local_tickets:
                results["processed"] += 1
                
                try:
                    result_type = await self._sync_ticket_outbound(
                        local_ticket,
                        manager,
                        integration,
                        sync_id
                    )
                    results[result_type] += 1
                    
                except Exception as e:
                    results["errors"] += 1
                    logger.error(
                        "Failed to sync local ticket",
                        error=str(e),
                        ticket_id=local_ticket.id,
                        **add_sync_context(sync_id, "outbound", integration.provider.value, "error")
                    )
            
            logger.info(
                "Outbound sync completed",
                **results,
                **add_sync_context(sync_id, "outbound", integration.provider.value, "completed", results["processed"])
            )
            
        except Exception as e:
            logger.error(
                "Outbound sync failed",
                error=str(e),
                **add_sync_context(sync_id, "outbound", integration.provider.value, "failed")
            )
            raise
        
        return results
    
    async def _sync_ticket_outbound(
        self,
        local_ticket: ITSMTicket,
        manager: Any,
        integration: ITSMIntegration,
        sync_id: str
    ) -> str:
        """Sync a single local ticket to remote system."""
        
        try:
            # Check if ticket exists in remote system
            remote_ticket = None
            if local_ticket.external_id:
                remote_ticket = await manager.get_ticket(local_ticket.external_id)
            
            # Map local data to remote format
            ticket_data = self._map_local_to_remote(local_ticket, integration)
            
            if remote_ticket:
                # Update existing remote ticket
                await manager.update_ticket(
                    local_ticket.external_id,
                    ticket_data
                )
                
                # Create sync record
                sync_record = ITSMSyncRecord(
                    integration_id=integration.id,
                    ticket_id=local_ticket.id,
                    sync_type="incremental",
                    direction="outbound",
                    status=SyncStatus.COMPLETED,
                    external_id=local_ticket.external_id,
                    external_table=local_ticket.external_table,
                    operation="update",
                    source_data=ticket_data,
                    target_data=remote_ticket,
                    success=True
                )
                
                result_type = "updated"
                
            else:
                # Create new remote ticket
                if integration.provider.value == "servicenow":
                    new_ticket = await manager.create_ticket(
                        ticket_data,
                        local_ticket.created_by or "system",
                        local_ticket.external_table
                    )
                    local_ticket.external_id = new_ticket.get("sys_id")
                    
                else:  # jira
                    # Need project key and issue type for Jira
                    project_key = ticket_data.get("project_key", "DEFAULT")
                    issue_type = ticket_data.get("issue_type", "Task")
                    
                    new_ticket = await manager.create_ticket(
                        ticket_data,
                        local_ticket.created_by or "system",
                        project_key,
                        issue_type
                    )
                    local_ticket.external_id = new_ticket.get("key")
                
                # Create sync record
                sync_record = ITSMSyncRecord(
                    integration_id=integration.id,
                    ticket_id=local_ticket.id,
                    sync_type="incremental",
                    direction="outbound",
                    status=SyncStatus.COMPLETED,
                    external_id=local_ticket.external_id,
                    external_table=local_ticket.external_table,
                    operation="create",
                    source_data=ticket_data,
                    target_data=new_ticket,
                    success=True
                )
                
                result_type = "created"
            
            # Update local ticket sync status
            local_ticket.last_synced_at = datetime.utcnow()
            local_ticket.local_changes = {}  # Clear local changes
            
            self.db_session.add(sync_record)
            await self.db_session.commit()
            
            return result_type
            
        except Exception as e:
            # Create failed sync record
            sync_record = ITSMSyncRecord(
                integration_id=integration.id,
                ticket_id=local_ticket.id,
                sync_type="incremental",
                direction="outbound",
                status=SyncStatus.FAILED,
                external_id=local_ticket.external_id,
                external_table=local_ticket.external_table,
                operation="update" if local_ticket.external_id else "create",
                success=False,
                error_message=str(e)
            )
            
            self.db_session.add(sync_record)
            await self.db_session.commit()
            
            raise
    
    def _map_remote_to_local(
        self,
        remote_ticket: Dict[str, Any],
        integration: ITSMIntegration
    ) -> Dict[str, Any]:
        """Map remote ticket data to local format."""
        
        mapped_data = {}
        
        if integration.provider.value == "servicenow":
            mapped_data.update({
                "title": remote_ticket.get("short_description"),
                "description": remote_ticket.get("description"),
                "assigned_to": remote_ticket.get("assigned_to"),
                "assigned_group": remote_ticket.get("assignment_group"),
                "reporter": remote_ticket.get("opened_by"),
                "created_date": self._parse_datetime(remote_ticket.get("sys_created_on")),
                "updated_date": self._parse_datetime(remote_ticket.get("sys_updated_on")),
                "resolved_date": self._parse_datetime(remote_ticket.get("resolved_at")),
                "closed_date": self._parse_datetime(remote_ticket.get("closed_at"))
            })
            
            # Map status
            state_map = {
                "1": TicketStatus.NEW,
                "2": TicketStatus.IN_PROGRESS,
                "4": TicketStatus.PENDING,
                "6": TicketStatus.RESOLVED,
                "7": TicketStatus.CLOSED,
                "8": TicketStatus.CANCELLED
            }
            mapped_data["status"] = state_map.get(remote_ticket.get("state"), TicketStatus.NEW)
            
            # Map priority
            priority_map = {
                "1": TicketPriority.EMERGENCY,
                "2": TicketPriority.CRITICAL,
                "3": TicketPriority.HIGH,
                "4": TicketPriority.MEDIUM,
                "5": TicketPriority.LOW
            }
            mapped_data["priority"] = priority_map.get(remote_ticket.get("priority"), TicketPriority.MEDIUM)
            
        else:  # jira
            mapped_data.update({
                "title": remote_ticket.get("summary"),
                "description": remote_ticket.get("description"),
                "assigned_to": remote_ticket.get("assignee"),
                "reporter": remote_ticket.get("reporter"),
                "created_date": self._parse_datetime(remote_ticket.get("created")),
                "updated_date": self._parse_datetime(remote_ticket.get("updated")),
                "due_date": self._parse_datetime(remote_ticket.get("duedate"))
            })
            
            # Map status - this would need custom mapping based on Jira workflow
            status = remote_ticket.get("status", "").lower()
            if "done" in status or "resolved" in status:
                mapped_data["status"] = TicketStatus.RESOLVED
            elif "closed" in status:
                mapped_data["status"] = TicketStatus.CLOSED
            elif "progress" in status:
                mapped_data["status"] = TicketStatus.IN_PROGRESS
            else:
                mapped_data["status"] = TicketStatus.NEW
            
            # Map priority
            priority = remote_ticket.get("priority", "").lower()
            if "highest" in priority:
                mapped_data["priority"] = TicketPriority.EMERGENCY
            elif "high" in priority:
                mapped_data["priority"] = TicketPriority.HIGH
            elif "low" in priority:
                mapped_data["priority"] = TicketPriority.LOW
            else:
                mapped_data["priority"] = TicketPriority.MEDIUM
        
        return mapped_data
    
    def _map_local_to_remote(
        self,
        local_ticket: ITSMTicket,
        integration: ITSMIntegration
    ) -> Dict[str, Any]:
        """Map local ticket data to remote format."""
        
        mapped_data = {}
        
        if integration.provider.value == "servicenow":
            mapped_data.update({
                "short_description": local_ticket.title,
                "description": local_ticket.description,
                "assigned_to": local_ticket.assigned_to,
                "assignment_group": local_ticket.assigned_group
            })
            
            # Map status
            state_map = {
                TicketStatus.NEW: "1",
                TicketStatus.IN_PROGRESS: "2",
                TicketStatus.PENDING: "4",
                TicketStatus.RESOLVED: "6",
                TicketStatus.CLOSED: "7",
                TicketStatus.CANCELLED: "8"
            }
            mapped_data["state"] = state_map.get(local_ticket.status, "1")
            
            # Map priority
            priority_map = {
                TicketPriority.EMERGENCY: "1",
                TicketPriority.CRITICAL: "2",
                TicketPriority.HIGH: "3",
                TicketPriority.MEDIUM: "4",
                TicketPriority.LOW: "5"
            }
            mapped_data["priority"] = priority_map.get(local_ticket.priority, "4")
            
        else:  # jira
            mapped_data.update({
                "summary": local_ticket.title,
                "description": local_ticket.description,
                "assignee": local_ticket.assigned_to
            })
            
            # Map priority
            priority_map = {
                TicketPriority.EMERGENCY: "Highest",
                TicketPriority.CRITICAL: "High",
                TicketPriority.HIGH: "High",
                TicketPriority.MEDIUM: "Medium",
                TicketPriority.LOW: "Low"
            }
            if local_ticket.priority in priority_map:
                mapped_data["priority"] = {"name": priority_map[local_ticket.priority]}
            
            if local_ticket.due_date:
                mapped_data["duedate"] = local_ticket.due_date.isoformat()
        
        # Add custom fields if present
        if local_ticket.custom_fields:
            mapped_data.update(local_ticket.custom_fields)
        
        return mapped_data
    
    def _parse_datetime(self, date_string: str) -> Optional[datetime]:
        """Parse datetime string to datetime object."""
        if not date_string:
            return None
        
        try:
            # Handle different datetime formats
            if 'T' in date_string:
                if date_string.endswith('Z'):
                    return datetime.fromisoformat(date_string.replace('Z', '+00:00'))
                else:
                    return datetime.fromisoformat(date_string)
            else:
                # Try parsing as date only
                return datetime.strptime(date_string, '%Y-%m-%d')
        except (ValueError, TypeError):
            logger.warning(f"Failed to parse datetime: {date_string}")
            return None
    
    async def _update_integration_sync_status(
        self,
        integration: ITSMIntegration,
        success: bool,
        error_message: str = None
    ) -> None:
        """Update integration sync status."""
        
        integration.last_sync_at = datetime.utcnow()
        
        if success:
            integration.successful_syncs += 1
            integration.health_status = "healthy"
            integration.last_error = None
        else:
            integration.failed_syncs += 1
            integration.health_status = "error"
            integration.last_error = error_message
        
        integration.total_syncs += 1
        
        await self.db_session.commit()
    
    async def resolve_conflict(
        self,
        ticket_id: str,
        conflict_id: str,
        resolution: str,
        resolution_data: Dict[str, Any] = None
    ) -> bool:
        """Resolve a synchronization conflict."""
        
        stmt = select(ITSMTicket).where(ITSMTicket.id == ticket_id)
        result = await self.db_session.execute(stmt)
        ticket = result.scalar_one_or_none()
        
        if not ticket:
            return False
        
        # Find and update the specific conflict
        for i, conflict in enumerate(ticket.sync_conflicts):
            if conflict.get("conflict_id") == conflict_id:
                conflict["resolution_status"] = "resolved"
                conflict["resolved_at"] = datetime.utcnow().isoformat()
                conflict["resolution"] = resolution
                
                if resolution_data:
                    conflict["resolution_data"] = resolution_data
                
                # Apply resolution based on strategy
                if resolution == ConflictResolution.AUTO_LOCAL:
                    # Keep local data, mark for outbound sync
                    ticket.local_changes["conflict_resolution"] = "local_wins"
                
                elif resolution == ConflictResolution.AUTO_REMOTE:
                    # Apply remote data
                    if "remote_data" in conflict.get("conflict_data", {}):
                        remote_data = conflict["conflict_data"]["remote_data"]
                        # Apply remote changes to local ticket
                        # This would need to be implemented based on specific fields
                
                elif resolution == "manual" and resolution_data:
                    # Apply manual resolution data
                    for field, value in resolution_data.items():
                        setattr(ticket, field, value)
                    ticket.local_changes["manual_resolution"] = resolution_data
                
                break
        
        await self.db_session.commit()
        return True
    
    async def get_sync_status(self, integration_id: str) -> Dict[str, Any]:
        """Get synchronization status for an integration."""
        
        stmt = select(ITSMIntegration).where(ITSMIntegration.id == integration_id)
        result = await self.db_session.execute(stmt)
        integration = result.scalar_one_or_none()
        
        if not integration:
            return None
        
        # Get recent sync records
        recent_syncs_stmt = select(ITSMSyncRecord).where(
            ITSMSyncRecord.integration_id == integration_id
        ).order_by(ITSMSyncRecord.created_at.desc()).limit(10)
        
        recent_syncs_result = await self.db_session.execute(recent_syncs_stmt)
        recent_syncs = recent_syncs_result.scalars().all()
        
        # Get pending conflicts
        conflicts_stmt = select(ITSMTicket).where(
            and_(
                ITSMTicket.integration_id == integration_id,
                ITSMTicket.sync_conflicts != []
            )
        )
        conflicts_result = await self.db_session.execute(conflicts_stmt)
        tickets_with_conflicts = conflicts_result.scalars().all()
        
        pending_conflicts = []
        for ticket in tickets_with_conflicts:
            for conflict in ticket.sync_conflicts:
                if conflict.get("resolution_status") == "pending":
                    pending_conflicts.append({
                        "ticket_id": ticket.id,
                        "conflict_id": conflict.get("conflict_id"),
                        "detected_at": conflict.get("detected_at"),
                        "conflict_data": conflict.get("conflict_data")
                    })
        
        return {
            "integration_id": integration_id,
            "health_status": integration.health_status,
            "last_sync_at": integration.last_sync_at.isoformat() if integration.last_sync_at else None,
            "total_syncs": integration.total_syncs,
            "successful_syncs": integration.successful_syncs,
            "failed_syncs": integration.failed_syncs,
            "last_error": integration.last_error,
            "sync_enabled": integration.sync_enabled,
            "recent_syncs": [
                {
                    "id": sync.id,
                    "direction": sync.direction,
                    "status": sync.status.value,
                    "operation": sync.operation,
                    "success": sync.success,
                    "error_message": sync.error_message,
                    "created_at": sync.created_at.isoformat()
                }
                for sync in recent_syncs
            ],
            "pending_conflicts": pending_conflicts,
            "is_running": integration_id in [sync_id.split("_")[1] for sync_id in self.running_syncs.keys()]
        }