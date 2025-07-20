"""
Workflow approval service for managing share approval workflows and requests.
"""

import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID, uuid4

from sqlalchemy import select, and_, or_, func, text, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import (
    get_database, ShareApprovalWorkflow, ShareApprovalRequest, ShareApprovalAction,
    ShareApprovalNotification, SharedResource
)
from app.models.sharing_models import (
    CreateApprovalWorkflowRequest, CreateApprovalRequestRequest, ApprovalActionRequest,
    ApprovalWorkflowResponse, ApprovalRequestResponse, ApprovalActionResponse,
    ApprovalWorkflowListRequest, ApprovalRequestListRequest, ApprovalStatistics,
    WorkflowStatus, ApprovalLevel, ApprovalAction, ApprovalTrigger,
    CreateShareRequest, ShareOperation, PermissionScope
)
import structlog

logger = structlog.get_logger(__name__)


class WorkflowApprovalError(Exception):
    """Exception raised for workflow approval errors."""
    pass


class ApprovalNotFoundError(Exception):
    """Exception raised when approval request is not found."""
    pass


class WorkflowApprovalService:
    """Service for managing approval workflows and requests."""

    async def create_workflow(
        self,
        request: CreateApprovalWorkflowRequest,
        user_id: str,
        db: Optional[AsyncSession] = None
    ) -> ApprovalWorkflowResponse:
        """Create a new approval workflow."""
        if db is None:
            db = await get_database()

        try:
            # Check if user has permission to create workflows
            from app.services.role_permission_service import role_permission_service
            permission_check = await role_permission_service.check_permission(
                user_id, ShareOperation.MANAGE_PERMISSIONS, PermissionScope.GLOBAL, db=db
            )
            
            if not permission_check.has_permission:
                raise WorkflowApprovalError("Insufficient permissions to create approval workflows")

            # Create workflow record
            workflow = ShareApprovalWorkflow(
                workflow_id=uuid4(),
                name=request.name,
                description=request.description,
                is_active=request.is_active,
                triggers=[trigger.value for trigger in request.triggers],
                trigger_conditions=request.trigger_conditions,
                approval_level=request.approval_level,
                required_approvers=request.required_approvers,
                optional_approvers=request.optional_approvers,
                approval_threshold=request.approval_threshold,
                auto_approve_after=request.auto_approve_after,
                expires_after=request.expires_after,
                reminder_intervals=request.reminder_intervals,
                escalation_enabled=request.escalation_enabled,
                escalation_after=request.escalation_after,
                escalation_approvers=request.escalation_approvers,
                allow_self_approval=request.allow_self_approval,
                require_reason=request.require_reason,
                parallel_approval=request.parallel_approval,
                notify_requester=request.notify_requester,
                notify_approvers=request.notify_approvers,
                notification_channels=request.notification_channels,
                created_by=user_id,
                tags=request.tags,
                metadata=request.metadata
            )

            db.add(workflow)
            await db.commit()
            await db.refresh(workflow)

            logger.info(
                "Approval workflow created",
                workflow_id=str(workflow.workflow_id),
                name=workflow.name,
                created_by=user_id
            )

            # Log audit event
            try:
                from app.services.audit_trail_service import audit_trail_service
                from app.models.sharing_models import AuditEventType, AuditEventSeverity, AuditEventCategory
                
                await audit_trail_service.log_event(
                    event_type=AuditEventType.CONFIGURATION_CHANGED,
                    category=AuditEventCategory.CONFIGURATION,
                    severity=AuditEventSeverity.MEDIUM,
                    title="Approval Workflow Created",
                    description=f"Created approval workflow: {workflow.name}",
                    user_id=user_id,
                    context={
                        "workflow_id": str(workflow.workflow_id),
                        "workflow_name": workflow.name,
                        "triggers": [trigger.value for trigger in request.triggers],
                        "approval_level": request.approval_level.value
                    },
                    db=db
                )
            except Exception as e:
                logger.warning("Failed to log audit event for workflow creation", error=str(e))

            return self._convert_workflow_to_response(workflow)

        except Exception as e:
            await db.rollback()
            logger.error("Failed to create approval workflow", error=str(e), name=request.name)
            raise

    async def get_workflow(
        self,
        workflow_id: UUID,
        user_id: str,
        db: Optional[AsyncSession] = None
    ) -> Optional[ApprovalWorkflowResponse]:
        """Get approval workflow by ID."""
        if db is None:
            db = await get_database()

        try:
            # Get workflow
            result = await db.execute(
                select(ShareApprovalWorkflow).where(ShareApprovalWorkflow.workflow_id == workflow_id)
            )
            workflow = result.scalar_one_or_none()

            if not workflow:
                return None

            # Check permissions
            await self._check_workflow_access_permission(workflow, user_id, db)

            return self._convert_workflow_to_response(workflow)

        except Exception as e:
            logger.error("Failed to get approval workflow", workflow_id=str(workflow_id), error=str(e))
            raise

    async def list_workflows(
        self,
        request: ApprovalWorkflowListRequest,
        user_id: str,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """List approval workflows with filtering and pagination."""
        if db is None:
            db = await get_database()

        try:
            # Build base query
            query = select(ShareApprovalWorkflow)

            # Apply filters
            if request.is_active is not None:
                query = query.where(ShareApprovalWorkflow.is_active == request.is_active)

            if request.triggers:
                # Filter workflows that have any of the specified triggers
                trigger_values = [trigger.value for trigger in request.triggers]
                query = query.where(
                    ShareApprovalWorkflow.triggers.op('@>')([trigger_values])
                )

            if request.created_by:
                query = query.where(ShareApprovalWorkflow.created_by == request.created_by)

            if request.tags:
                for tag in request.tags:
                    query = query.where(ShareApprovalWorkflow.tags.contains([tag]))

            if request.search:
                search_term = f"%{request.search}%"
                query = query.where(
                    or_(
                        ShareApprovalWorkflow.name.ilike(search_term),
                        ShareApprovalWorkflow.description.ilike(search_term)
                    )
                )

            # Get total count
            count_result = await db.execute(
                select(func.count()).select_from(query.subquery())
            )
            total = count_result.scalar()

            # Apply sorting
            if request.sort_by == "name":
                sort_column = ShareApprovalWorkflow.name
            elif request.sort_by == "updated_at":
                sort_column = ShareApprovalWorkflow.updated_at
            else:  # created_at
                sort_column = ShareApprovalWorkflow.created_at

            if request.sort_order == "asc":
                query = query.order_by(sort_column.asc())
            else:
                query = query.order_by(sort_column.desc())

            # Apply pagination
            query = query.offset(request.offset).limit(request.limit)

            # Execute query
            result = await db.execute(query)
            workflows = result.scalars().all()

            # Convert to response models
            workflow_responses = []
            for workflow in workflows:
                try:
                    await self._check_workflow_access_permission(workflow, user_id, db)
                    workflow_responses.append(self._convert_workflow_to_response(workflow))
                except:
                    # Skip workflows user doesn't have access to
                    continue

            return {
                "items": workflow_responses,
                "total": total,
                "limit": request.limit,
                "offset": request.offset,
                "has_more": request.offset + len(workflow_responses) < total
            }

        except Exception as e:
            logger.error("Failed to list approval workflows", error=str(e))
            raise

    async def create_approval_request(
        self,
        request: CreateApprovalRequestRequest,
        user_id: str,
        db: Optional[AsyncSession] = None
    ) -> ApprovalRequestResponse:
        """Create a new approval request."""
        if db is None:
            db = await get_database()

        try:
            # Get workflow
            workflow_result = await db.execute(
                select(ShareApprovalWorkflow).where(ShareApprovalWorkflow.workflow_id == request.workflow_id)
            )
            workflow = workflow_result.scalar_one_or_none()

            if not workflow:
                raise ApprovalNotFoundError("Workflow not found")

            if not workflow.is_active:
                raise WorkflowApprovalError("Workflow is not active")

            # Calculate timing
            now = datetime.now(timezone.utc)
            auto_approve_at = None
            expires_at = None

            if workflow.auto_approve_after:
                auto_approve_at = now + timedelta(hours=workflow.auto_approve_after)

            if workflow.expires_after:
                expires_at = now + timedelta(hours=workflow.expires_after)
            elif request.requested_approval_by:
                expires_at = request.requested_approval_by

            # Determine initial approvers
            current_approvers = workflow.required_approvers.copy()
            if workflow.optional_approvers and workflow.approval_level == ApprovalLevel.MAJORITY:
                current_approvers.extend(workflow.optional_approvers)

            # Filter out self if self-approval not allowed
            if not workflow.allow_self_approval and user_id in current_approvers:
                current_approvers.remove(user_id)

            if not current_approvers:
                raise WorkflowApprovalError("No valid approvers available for this workflow")

            # Create approval request
            approval_request = ShareApprovalRequest(
                request_id=uuid4(),
                workflow_id=request.workflow_id,
                share_request=json.loads(request.share_request.model_dump_json()),
                justification=request.justification,
                priority=request.priority,
                business_case=request.business_case,
                risk_assessment=request.risk_assessment,
                compliance_notes=request.compliance_notes,
                requested_approval_by=request.requested_approval_by,
                auto_approve_at=auto_approve_at,
                expires_at=expires_at,
                current_approvers=current_approvers,
                pending_approvals=current_approvers.copy(),
                requested_by=user_id,
                attachments=request.attachments,
                references=request.references,
                metadata=request.metadata
            )

            db.add(approval_request)

            # Update workflow statistics
            workflow.total_requests += 1
            workflow.pending_requests += 1

            await db.commit()
            await db.refresh(approval_request)

            logger.info(
                "Approval request created",
                request_id=str(approval_request.request_id),
                workflow_id=str(request.workflow_id),
                requested_by=user_id
            )

            # Send notifications to approvers
            await self._send_approval_notifications(approval_request, workflow, "request_created", db)

            # Log audit event
            try:
                from app.services.audit_trail_service import audit_trail_service
                from app.models.sharing_models import AuditEventType, AuditEventSeverity, AuditEventCategory
                
                await audit_trail_service.log_event(
                    event_type=AuditEventType.SHARE_CREATED,
                    category=AuditEventCategory.SHARE_MANAGEMENT,
                    severity=AuditEventSeverity.MEDIUM,
                    title="Approval Request Created",
                    description=f"Created approval request for share: {request.share_request.resource_name}",
                    user_id=user_id,
                    context={
                        "request_id": str(approval_request.request_id),
                        "workflow_id": str(request.workflow_id),
                        "resource_type": request.share_request.resource_type.value,
                        "priority": request.priority,
                        "approvers": current_approvers
                    },
                    db=db
                )
            except Exception as e:
                logger.warning("Failed to log audit event for approval request creation", error=str(e))

            return self._convert_request_to_response(approval_request, workflow)

        except Exception as e:
            await db.rollback()
            logger.error("Failed to create approval request", error=str(e))
            raise

    async def take_action(
        self,
        request_id: UUID,
        action_request: ApprovalActionRequest,
        user_id: str,
        db: Optional[AsyncSession] = None
    ) -> ApprovalActionResponse:
        """Take action on an approval request."""
        if db is None:
            db = await get_database()

        try:
            # Get approval request with workflow
            result = await db.execute(
                select(ShareApprovalRequest)
                .options(selectinload(ShareApprovalRequest.workflow))
                .where(ShareApprovalRequest.request_id == request_id)
            )
            approval_request = result.scalar_one_or_none()

            if not approval_request:
                raise ApprovalNotFoundError("Approval request not found")

            workflow = approval_request.workflow

            # Validate action is allowed
            if approval_request.status != WorkflowStatus.PENDING:
                raise WorkflowApprovalError(f"Cannot take action on {approval_request.status.value} request")

            # Check if user is authorized to take action
            if user_id not in approval_request.current_approvers:
                raise WorkflowApprovalError("User not authorized to approve this request")

            # Handle delegation
            if action_request.action == ApprovalAction.DELEGATE:
                if not action_request.delegate_to:
                    raise WorkflowApprovalError("delegate_to is required for delegation")
                
                # Update current approvers
                approval_request.current_approvers = [
                    action_request.delegate_to if approver == user_id else approver
                    for approver in approval_request.current_approvers
                ]
                approval_request.pending_approvals = [
                    action_request.delegate_to if approver == user_id else approver
                    for approver in approval_request.pending_approvals
                ]

            else:
                # Remove user from pending approvals
                if user_id in approval_request.pending_approvals:
                    approval_request.pending_approvals.remove(user_id)

            # Create action record
            action = ShareApprovalAction(
                action_id=uuid4(),
                request_id=request_id,
                approver_id=user_id,
                action=action_request.action,
                reason=action_request.reason,
                delegate_to=action_request.delegate_to,
                conditions=action_request.conditions,
                notes=action_request.notes,
                metadata=action_request.metadata
            )

            db.add(action)

            # Update completed approvals
            approval_request.completed_approvals.append({
                "action_id": str(action.action_id),
                "approver_id": user_id,
                "action": action_request.action.value,
                "reason": action_request.reason,
                "taken_at": datetime.now(timezone.utc).isoformat(),
                "delegate_to": action_request.delegate_to,
                "conditions": action_request.conditions
            })

            # Determine if request should be resolved
            if action_request.action == ApprovalAction.REJECT:
                approval_request.status = WorkflowStatus.REJECTED
                approval_request.final_action = ApprovalAction.REJECT
                approval_request.final_reason = action_request.reason
                approval_request.rejected_by = user_id
                approval_request.rejected_at = datetime.now(timezone.utc)
                
                # Update workflow statistics
                workflow.pending_requests -= 1
                workflow.rejected_requests += 1

            elif action_request.action == ApprovalAction.APPROVE:
                # Check if all required approvals are complete
                if self._is_approval_complete(approval_request, workflow):
                    approval_request.status = WorkflowStatus.APPROVED
                    approval_request.final_action = ApprovalAction.APPROVE
                    approval_request.final_reason = "All required approvals obtained"
                    approval_request.approved_by = user_id
                    approval_request.approved_at = datetime.now(timezone.utc)
                    
                    # Create the actual share
                    share_response = await self._create_approved_share(approval_request, db)
                    approval_request.share_id = share_response.share_id
                    
                    # Update workflow statistics
                    workflow.pending_requests -= 1
                    workflow.approved_requests += 1
                    
                    # Calculate approval time
                    approval_time = (approval_request.approved_at - approval_request.created_at).total_seconds() / 3600
                    if workflow.average_approval_time is None:
                        workflow.average_approval_time = approval_time
                    else:
                        # Running average
                        total_approved = workflow.approved_requests
                        workflow.average_approval_time = (
                            (workflow.average_approval_time * (total_approved - 1) + approval_time) / total_approved
                        )

            await db.commit()
            await db.refresh(action)

            # Send notifications
            notification_type = f"request_{action_request.action.value}"
            await self._send_approval_notifications(approval_request, workflow, notification_type, db)

            logger.info(
                "Approval action taken",
                action_id=str(action.action_id),
                request_id=str(request_id),
                action=action_request.action.value,
                approver_id=user_id
            )

            return ApprovalActionResponse(
                action_id=action.action_id,
                request_id=action.request_id,
                approver_id=action.approver_id,
                action=action.action,
                reason=action.reason,
                status=action.status,
                delegate_to=action.delegate_to,
                conditions=action.conditions,
                notes=action.notes,
                taken_at=action.taken_at,
                metadata=action.metadata
            )

        except Exception as e:
            await db.rollback()
            logger.error("Failed to take approval action", request_id=str(request_id), error=str(e))
            raise

    async def list_approval_requests(
        self,
        request: ApprovalRequestListRequest,
        user_id: str,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """List approval requests with filtering and pagination."""
        if db is None:
            db = await get_database()

        try:
            # Build base query
            query = select(ShareApprovalRequest).options(selectinload(ShareApprovalRequest.workflow))

            # Apply filters based on user permissions
            from app.services.role_permission_service import role_permission_service
            global_permission = await role_permission_service.check_permission(
                user_id, ShareOperation.VIEW_ANALYTICS, PermissionScope.GLOBAL, db=db
            )

            if not global_permission.has_permission:
                # User can only see their own requests or requests they can approve
                query = query.where(
                    or_(
                        ShareApprovalRequest.requested_by == user_id,
                        ShareApprovalRequest.current_approvers.contains([user_id])
                    )
                )

            # Apply additional filters
            if request.workflow_id:
                query = query.where(ShareApprovalRequest.workflow_id == request.workflow_id)

            if request.status:
                query = query.where(ShareApprovalRequest.status == request.status)

            if request.priority:
                query = query.where(ShareApprovalRequest.priority == request.priority)

            if request.requested_by:
                query = query.where(ShareApprovalRequest.requested_by == request.requested_by)

            if request.assigned_to:
                query = query.where(ShareApprovalRequest.current_approvers.contains([request.assigned_to]))

            # Time filtering
            if request.created_after:
                query = query.where(ShareApprovalRequest.created_at >= request.created_after)

            if request.created_before:
                query = query.where(ShareApprovalRequest.created_at <= request.created_before)

            if request.due_after:
                query = query.where(ShareApprovalRequest.requested_approval_by >= request.due_after)

            if request.due_before:
                query = query.where(ShareApprovalRequest.requested_approval_by <= request.due_before)

            # Search
            if request.search:
                search_term = f"%{request.search}%"
                query = query.where(
                    or_(
                        ShareApprovalRequest.justification.ilike(search_term),
                        ShareApprovalRequest.business_case.ilike(search_term)
                    )
                )

            # Get total count
            count_result = await db.execute(
                select(func.count()).select_from(query.subquery())
            )
            total = count_result.scalar()

            # Apply sorting
            if request.sort_by == "updated_at":
                sort_column = ShareApprovalRequest.updated_at
            elif request.sort_by == "priority":
                sort_column = ShareApprovalRequest.priority
            elif request.sort_by == "status":
                sort_column = ShareApprovalRequest.status
            else:  # created_at
                sort_column = ShareApprovalRequest.created_at

            if request.sort_order == "asc":
                query = query.order_by(sort_column.asc())
            else:
                query = query.order_by(sort_column.desc())

            # Apply pagination
            query = query.offset(request.offset).limit(request.limit)

            # Execute query
            result = await db.execute(query)
            requests = result.scalars().all()

            # Convert to response models
            request_responses = []
            for req in requests:
                request_responses.append(self._convert_request_to_response(req, req.workflow))

            return {
                "items": request_responses,
                "total": total,
                "limit": request.limit,
                "offset": request.offset,
                "has_more": request.offset + len(request_responses) < total
            }

        except Exception as e:
            logger.error("Failed to list approval requests", error=str(e))
            raise

    async def get_approval_statistics(
        self,
        user_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        db: Optional[AsyncSession] = None
    ) -> ApprovalStatistics:
        """Get approval workflow statistics."""
        if db is None:
            db = await get_database()

        try:
            # Check permissions
            from app.services.role_permission_service import role_permission_service
            permission_check = await role_permission_service.check_permission(
                user_id, ShareOperation.VIEW_ANALYTICS, PermissionScope.GLOBAL, db=db
            )
            
            if not permission_check.has_permission:
                raise WorkflowApprovalError("Insufficient permissions to view approval statistics")

            # Set default time range if not provided
            if not end_time:
                end_time = datetime.now(timezone.utc)
            if not start_time:
                start_time = end_time - timedelta(days=30)

            # Get workflow statistics
            workflow_count_result = await db.execute(
                select(func.count(ShareApprovalWorkflow.workflow_id))
            )
            total_workflows = workflow_count_result.scalar() or 0

            active_workflow_result = await db.execute(
                select(func.count(ShareApprovalWorkflow.workflow_id))
                .where(ShareApprovalWorkflow.is_active == True)
            )
            active_workflows = active_workflow_result.scalar() or 0

            # Get request statistics
            request_stats = await db.execute(
                select(
                    func.count(ShareApprovalRequest.request_id).label("total"),
                    func.sum(func.case((ShareApprovalRequest.status == WorkflowStatus.PENDING, 1), else_=0)).label("pending"),
                    func.sum(func.case((ShareApprovalRequest.status == WorkflowStatus.APPROVED, 1), else_=0)).label("approved"),
                    func.sum(func.case((ShareApprovalRequest.status == WorkflowStatus.REJECTED, 1), else_=0)).label("rejected"),
                    func.sum(func.case((ShareApprovalRequest.status == WorkflowStatus.EXPIRED, 1), else_=0)).label("expired")
                )
                .where(
                    and_(
                        ShareApprovalRequest.created_at >= start_time,
                        ShareApprovalRequest.created_at <= end_time
                    )
                )
            )
            stats = request_stats.first()

            total_requests = stats.total or 0
            pending_requests = stats.pending or 0
            approved_requests = stats.approved or 0
            rejected_requests = stats.rejected or 0
            expired_requests = stats.expired or 0

            # Calculate approval rate
            completed_requests = approved_requests + rejected_requests
            approval_rate = (approved_requests / completed_requests * 100) if completed_requests > 0 else 0

            # Get average approval time
            avg_time_result = await db.execute(
                select(func.avg(
                    func.extract('epoch', ShareApprovalRequest.approved_at - ShareApprovalRequest.created_at) / 3600
                ))
                .where(
                    and_(
                        ShareApprovalRequest.status == WorkflowStatus.APPROVED,
                        ShareApprovalRequest.created_at >= start_time,
                        ShareApprovalRequest.created_at <= end_time
                    )
                )
            )
            average_approval_time = avg_time_result.scalar()

            # Get median approval time
            median_time_result = await db.execute(
                select(func.percentile_cont(0.5).within_group(
                    func.extract('epoch', ShareApprovalRequest.approved_at - ShareApprovalRequest.created_at) / 3600
                ))
                .where(
                    and_(
                        ShareApprovalRequest.status == WorkflowStatus.APPROVED,
                        ShareApprovalRequest.created_at >= start_time,
                        ShareApprovalRequest.created_at <= end_time
                    )
                )
            )
            median_approval_time = median_time_result.scalar()

            return ApprovalStatistics(
                total_workflows=total_workflows,
                active_workflows=active_workflows,
                total_requests=total_requests,
                pending_requests=pending_requests,
                approved_requests=approved_requests,
                rejected_requests=rejected_requests,
                expired_requests=expired_requests,
                average_approval_time_hours=average_approval_time,
                median_approval_time_hours=median_approval_time,
                approval_rate_percentage=approval_rate,
                workflows_by_trigger={},  # Would implement detailed queries
                requests_by_priority={},
                requests_by_status={
                    WorkflowStatus.PENDING: pending_requests,
                    WorkflowStatus.APPROVED: approved_requests,
                    WorkflowStatus.REJECTED: rejected_requests,
                    WorkflowStatus.EXPIRED: expired_requests
                },
                top_requesters=[],
                top_approvers=[],
                most_active_workflows=[],
                requests_by_day=[],
                approval_time_trends=[],
                high_risk_requests=0,
                compliance_review_requests=0,
                escalated_requests=0
            )

        except Exception as e:
            logger.error("Failed to get approval statistics", error=str(e))
            raise

    def _convert_workflow_to_response(self, workflow: ShareApprovalWorkflow) -> ApprovalWorkflowResponse:
        """Convert database model to response model."""
        return ApprovalWorkflowResponse(
            workflow_id=workflow.workflow_id,
            name=workflow.name,
            description=workflow.description,
            is_active=workflow.is_active,
            triggers=[ApprovalTrigger(trigger) for trigger in workflow.triggers],
            trigger_conditions=workflow.trigger_conditions,
            approval_level=workflow.approval_level,
            required_approvers=workflow.required_approvers,
            optional_approvers=workflow.optional_approvers,
            approval_threshold=workflow.approval_threshold,
            auto_approve_after=workflow.auto_approve_after,
            expires_after=workflow.expires_after,
            reminder_intervals=workflow.reminder_intervals,
            escalation_enabled=workflow.escalation_enabled,
            escalation_after=workflow.escalation_after,
            escalation_approvers=workflow.escalation_approvers,
            allow_self_approval=workflow.allow_self_approval,
            require_reason=workflow.require_reason,
            parallel_approval=workflow.parallel_approval,
            total_requests=workflow.total_requests,
            approved_requests=workflow.approved_requests,
            rejected_requests=workflow.rejected_requests,
            pending_requests=workflow.pending_requests,
            average_approval_time=workflow.average_approval_time,
            created_by=workflow.created_by,
            created_at=workflow.created_at,
            updated_at=workflow.updated_at,
            tags=workflow.tags,
            metadata=workflow.metadata
        )

    def _convert_request_to_response(
        self, 
        request: ShareApprovalRequest, 
        workflow: ShareApprovalWorkflow
    ) -> ApprovalRequestResponse:
        """Convert database model to response model."""
        return ApprovalRequestResponse(
            request_id=request.request_id,
            workflow_id=request.workflow_id,
            share_id=request.share_id,
            share_request=request.share_request,
            justification=request.justification,
            priority=request.priority,
            status=request.status,
            business_case=request.business_case,
            risk_assessment=request.risk_assessment,
            compliance_notes=request.compliance_notes,
            requested_approval_by=request.requested_approval_by,
            auto_approve_at=request.auto_approve_at,
            expires_at=request.expires_at,
            current_approvers=request.current_approvers,
            completed_approvals=request.completed_approvals,
            pending_approvals=request.pending_approvals,
            escalated=request.escalated,
            escalated_at=request.escalated_at,
            final_action=request.final_action,
            final_reason=request.final_reason,
            approved_by=request.approved_by,
            approved_at=request.approved_at,
            rejected_by=request.rejected_by,
            rejected_at=request.rejected_at,
            requested_by=request.requested_by,
            created_at=request.created_at,
            updated_at=request.updated_at,
            attachments=request.attachments,
            references=request.references,
            metadata=request.metadata
        )

    async def _check_workflow_access_permission(
        self,
        workflow: ShareApprovalWorkflow,
        user_id: str,
        db: AsyncSession
    ) -> None:
        """Check if user has access to workflow."""
        from app.services.role_permission_service import role_permission_service
        
        # Check if user has global permissions or is the creator
        if workflow.created_by == user_id:
            return
            
        permission_check = await role_permission_service.check_permission(
            user_id, ShareOperation.VIEW_ANALYTICS, PermissionScope.GLOBAL, db=db
        )
        
        if not permission_check.has_permission:
            raise WorkflowApprovalError("Insufficient permissions to access this workflow")

    def _is_approval_complete(
        self,
        request: ShareApprovalRequest,
        workflow: ShareApprovalWorkflow
    ) -> bool:
        """Check if approval is complete based on workflow rules."""
        if workflow.approval_level == ApprovalLevel.SINGLE:
            return True  # Single approval is enough
        
        elif workflow.approval_level == ApprovalLevel.UNANIMOUS:
            # All required approvers must approve
            approved_count = len([
                approval for approval in request.completed_approvals
                if approval.get("action") == "approve"
            ])
            return approved_count >= len(workflow.required_approvers)
        
        elif workflow.approval_level == ApprovalLevel.MAJORITY:
            # Majority of approvers must approve
            total_approvers = len(workflow.required_approvers)
            if workflow.optional_approvers:
                total_approvers += len(workflow.optional_approvers)
            
            approved_count = len([
                approval for approval in request.completed_approvals
                if approval.get("action") == "approve"
            ])
            return approved_count > (total_approvers / 2)
        
        elif workflow.approval_level == ApprovalLevel.MULTI_LEVEL:
            # Use approval threshold
            approved_count = len([
                approval for approval in request.completed_approvals
                if approval.get("action") == "approve"
            ])
            return approved_count >= (workflow.approval_threshold or 1)
        
        return False

    async def _create_approved_share(
        self,
        approval_request: ShareApprovalRequest,
        db: AsyncSession
    ) -> Any:
        """Create the actual share after approval."""
        from app.services.sharing_service import sharing_service
        from app.models.sharing_models import CreateShareRequest
        
        # Convert back to CreateShareRequest
        share_request_data = approval_request.share_request
        share_request = CreateShareRequest(**share_request_data)
        
        # Create the share
        return await sharing_service.create_share(share_request, approval_request.requested_by, db)

    async def _send_approval_notifications(
        self,
        request: ShareApprovalRequest,
        workflow: ShareApprovalWorkflow,
        notification_type: str,
        db: AsyncSession
    ) -> None:
        """Send notifications for approval events."""
        try:
            # This would integrate with notification service
            # For now, just log the notification
            logger.info(
                "Approval notification would be sent",
                request_id=str(request.request_id),
                notification_type=notification_type,
                recipients=request.current_approvers if notification_type.startswith("request_") else [request.requested_by]
            )
        except Exception as e:
            logger.warning("Failed to send approval notifications", error=str(e))


# Service instance
workflow_approval_service = WorkflowApprovalService()