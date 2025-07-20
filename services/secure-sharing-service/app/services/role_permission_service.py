"""
Role-based permission service for secure sharing.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID, uuid4

from sqlalchemy import select, and_, or_, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_database, ShareRolePermissions, SharePermissionAuditLog, ShareRoleDefinitions
from app.models.sharing_models import (
    ShareRole, ShareOperation, PermissionScope, ShareType,
    CreateRolePermissionRequest, UpdateRolePermissionRequest, RolePermissionResponse,
    UserRolePermissionsResponse, RolePermissionCheck, PermissionAuditLog,
    SharePermissionMatrix, BulkRoleOperation
)
import structlog

logger = structlog.get_logger(__name__)


class RolePermissionError(Exception):
    """Exception raised for role permission errors."""
    pass


class InsufficientPermissionError(Exception):
    """Exception raised when user lacks required permissions."""
    pass


class RolePermissionService:
    """Service for managing role-based permissions."""

    # Default role definitions
    DEFAULT_ROLE_PERMISSIONS = {
        ShareRole.ADMIN: {
            "operations": [op.value for op in ShareOperation],
            "scopes": [scope.value for scope in PermissionScope],
            "description": "Full access to all sharing operations and management",
            "priority": 100
        },
        ShareRole.MANAGER: {
            "operations": [
                ShareOperation.CREATE.value, ShareOperation.READ.value, ShareOperation.UPDATE.value,
                ShareOperation.DELETE.value, ShareOperation.SHARE.value, ShareOperation.REVOKE.value,
                ShareOperation.VIEW_ANALYTICS.value
            ],
            "scopes": [PermissionScope.GLOBAL.value, PermissionScope.RESOURCE_TYPE.value, PermissionScope.RESOURCE.value],
            "description": "Manage shares within assigned scope",
            "priority": 80
        },
        ShareRole.CREATOR: {
            "operations": [
                ShareOperation.CREATE.value, ShareOperation.READ.value, ShareOperation.UPDATE.value,
                ShareOperation.DELETE.value, ShareOperation.SHARE.value, ShareOperation.REVOKE.value
            ],
            "scopes": [PermissionScope.RESOURCE.value, PermissionScope.SHARE.value],
            "description": "Create and manage own shares",
            "priority": 60
        },
        ShareRole.MEMBER: {
            "operations": [
                ShareOperation.READ.value, ShareOperation.SHARE.value
            ],
            "scopes": [PermissionScope.RESOURCE.value, PermissionScope.SHARE.value],
            "description": "View and share existing resources",
            "priority": 40
        },
        ShareRole.VIEWER: {
            "operations": [ShareOperation.READ.value],
            "scopes": [PermissionScope.SHARE.value],
            "description": "View shared resources only",
            "priority": 20
        }
    }

    async def initialize_default_roles(
        self,
        admin_user_id: str,
        db: Optional[AsyncSession] = None
    ) -> None:
        """Initialize default role definitions."""
        if db is None:
            db = await get_database()

        try:
            for role, config in self.DEFAULT_ROLE_PERMISSIONS.items():
                # Check if role already exists
                result = await db.execute(
                    select(ShareRoleDefinitions).where(ShareRoleDefinitions.role == role)
                )
                existing_role = result.scalar_one_or_none()

                if not existing_role:
                    role_def = ShareRoleDefinitions(
                        definition_id=uuid4(),
                        role=role,
                        display_name=role.value.title(),
                        description=config["description"],
                        default_operations=config["operations"],
                        allowed_scopes=config["scopes"],
                        priority=config["priority"],
                        is_system_role=True,
                        is_assignable=True,
                        created_by=admin_user_id
                    )
                    db.add(role_def)

            await db.commit()
            logger.info("Default role definitions initialized", admin_user_id=admin_user_id)

        except Exception as e:
            await db.rollback()
            logger.error("Failed to initialize default roles", error=str(e))
            raise

    async def assign_role_permission(
        self,
        request: CreateRolePermissionRequest,
        assigned_by: str,
        db: Optional[AsyncSession] = None
    ) -> RolePermissionResponse:
        """Assign a role permission to a user."""
        if db is None:
            db = await get_database()

        try:
            # Check if requester has permission to assign this role
            has_permission = await self.check_permission(
                assigned_by, ShareOperation.MANAGE_PERMISSIONS, request.scope, request.scope_id, db
            )
            
            if not has_permission.has_permission:
                raise InsufficientPermissionError("Insufficient permissions to assign roles")

            # Get role definition
            role_def = await self._get_role_definition(request.role, db)
            if not role_def:
                raise RolePermissionError(f"Role {request.role.value} not found")

            # Check if permission already exists
            existing = await db.execute(
                select(ShareRolePermissions).where(
                    and_(
                        ShareRolePermissions.user_id == request.user_id,
                        ShareRolePermissions.role == request.role,
                        ShareRolePermissions.scope == request.scope,
                        ShareRolePermissions.scope_id == request.scope_id
                    )
                )
            )
            existing_permission = existing.scalar_one_or_none()

            if existing_permission:
                if existing_permission.active:
                    raise RolePermissionError("User already has this role permission")
                else:
                    # Reactivate existing permission
                    existing_permission.active = True
                    existing_permission.expires_at = request.expires_at
                    existing_permission.conditions = request.conditions
                    existing_permission.updated_at = datetime.now(timezone.utc)
                    permission = existing_permission
            else:
                # Create new permission
                permission = ShareRolePermissions(
                    permission_id=uuid4(),
                    user_id=request.user_id,
                    role=request.role,
                    scope=request.scope,
                    scope_id=request.scope_id,
                    resource_types=[rt.value for rt in request.resource_types] if request.resource_types else None,
                    operations=role_def.default_operations,
                    conditions=request.conditions,
                    expires_at=request.expires_at,
                    created_by=assigned_by
                )
                db.add(permission)

            await db.commit()
            await db.refresh(permission)

            # Log the assignment
            await self._log_permission_audit(
                user_id=request.user_id,
                operation=ShareOperation.MANAGE_PERMISSIONS,
                scope=request.scope,
                scope_id=request.scope_id,
                permission_granted=True,
                granted_by_role=request.role,
                granted_by_permission_id=permission.permission_id,
                db=db
            )

            logger.info(
                "Role permission assigned",
                user_id=request.user_id,
                role=request.role.value,
                scope=request.scope.value,
                assigned_by=assigned_by
            )

            return RolePermissionResponse(
                permission_id=permission.permission_id,
                user_id=permission.user_id,
                role=permission.role,
                scope=permission.scope,
                scope_id=permission.scope_id,
                resource_types=[ShareType(rt) for rt in permission.resource_types] if permission.resource_types else None,
                operations=[ShareOperation(op) for op in permission.operations],
                conditions=permission.conditions,
                active=permission.active,
                expires_at=permission.expires_at,
                created_by=permission.created_by,
                created_at=permission.created_at,
                updated_at=permission.updated_at
            )

        except Exception as e:
            await db.rollback()
            logger.error(
                "Failed to assign role permission",
                user_id=request.user_id,
                role=request.role.value,
                error=str(e)
            )
            raise

    async def check_permission(
        self,
        user_id: str,
        operation: ShareOperation,
        scope: PermissionScope,
        scope_id: Optional[str] = None,
        resource_type: Optional[ShareType] = None,
        share_id: Optional[UUID] = None,
        db: Optional[AsyncSession] = None
    ) -> RolePermissionCheck:
        """Check if user has permission for an operation."""
        if db is None:
            db = await get_database()

        try:
            # Get user's active permissions
            current_time = datetime.now(timezone.utc)
            query = select(ShareRolePermissions).where(
                and_(
                    ShareRolePermissions.user_id == user_id,
                    ShareRolePermissions.active == True,
                    or_(
                        ShareRolePermissions.expires_at.is_(None),
                        ShareRolePermissions.expires_at > current_time
                    )
                )
            )

            result = await db.execute(query)
            permissions = result.scalars().all()

            # Check permissions in priority order
            matching_permissions = []
            for permission in permissions:
                if await self._permission_matches(permission, operation, scope, scope_id, resource_type):
                    matching_permissions.append(permission)

            # Sort by role priority (higher priority first)
            role_priorities = {role: config["priority"] for role, config in self.DEFAULT_ROLE_PERMISSIONS.items()}
            matching_permissions.sort(key=lambda p: role_priorities.get(p.role, 0), reverse=True)

            if matching_permissions:
                permission = matching_permissions[0]
                result = RolePermissionCheck(
                    user_id=user_id,
                    operation=operation,
                    scope=scope,
                    scope_id=scope_id,
                    resource_type=resource_type,
                    share_id=share_id,
                    has_permission=True,
                    granted_by_role=permission.role,
                    granted_by_permission_id=permission.permission_id,
                    reason=f"Granted by {permission.role.value} role"
                )
            else:
                result = RolePermissionCheck(
                    user_id=user_id,
                    operation=operation,
                    scope=scope,
                    scope_id=scope_id,
                    resource_type=resource_type,
                    share_id=share_id,
                    has_permission=False,
                    reason="No matching permissions found"
                )

            # Log the permission check
            await self._log_permission_audit(
                user_id=user_id,
                operation=operation,
                scope=scope,
                scope_id=scope_id,
                resource_type=resource_type,
                share_id=share_id,
                permission_granted=result.has_permission,
                granted_by_role=result.granted_by_role,
                granted_by_permission_id=result.granted_by_permission_id,
                db=db
            )

            return result

        except Exception as e:
            logger.error(
                "Permission check failed",
                user_id=user_id,
                operation=operation.value,
                error=str(e)
            )
            # Default deny on error
            return RolePermissionCheck(
                user_id=user_id,
                operation=operation,
                scope=scope,
                scope_id=scope_id,
                resource_type=resource_type,
                share_id=share_id,
                has_permission=False,
                reason=f"Permission check failed: {str(e)}"
            )

    async def get_user_permissions(
        self,
        user_id: str,
        include_expired: bool = False,
        db: Optional[AsyncSession] = None
    ) -> UserRolePermissionsResponse:
        """Get all permissions for a user."""
        if db is None:
            db = await get_database()

        try:
            current_time = datetime.now(timezone.utc)
            query = select(ShareRolePermissions).where(ShareRolePermissions.user_id == user_id)
            
            if not include_expired:
                query = query.where(
                    and_(
                        ShareRolePermissions.active == True,
                        or_(
                            ShareRolePermissions.expires_at.is_(None),
                            ShareRolePermissions.expires_at > current_time
                        )
                    )
                )

            result = await db.execute(query)
            permissions = result.scalars().all()

            # Convert to response models
            permission_responses = []
            for permission in permissions:
                permission_responses.append(RolePermissionResponse(
                    permission_id=permission.permission_id,
                    user_id=permission.user_id,
                    role=permission.role,
                    scope=permission.scope,
                    scope_id=permission.scope_id,
                    resource_types=[ShareType(rt) for rt in permission.resource_types] if permission.resource_types else None,
                    operations=[ShareOperation(op) for op in permission.operations],
                    conditions=permission.conditions,
                    active=permission.active,
                    expires_at=permission.expires_at,
                    created_by=permission.created_by,
                    created_at=permission.created_at,
                    updated_at=permission.updated_at
                ))

            # Calculate effective operations by scope
            effective_operations = {}
            for scope in PermissionScope:
                scope_operations = set()
                for permission in permissions:
                    if permission.active and (not permission.expires_at or permission.expires_at > current_time):
                        if permission.scope == scope or permission.scope == PermissionScope.GLOBAL:
                            scope_operations.update(permission.operations)
                effective_operations[scope.value] = list(scope_operations)

            # Check specific capabilities
            global_ops = set(effective_operations.get(PermissionScope.GLOBAL.value, []))
            can_create_shares = ShareOperation.CREATE.value in global_ops
            can_manage_permissions = ShareOperation.MANAGE_PERMISSIONS.value in global_ops
            can_view_analytics = ShareOperation.VIEW_ANALYTICS.value in global_ops

            return UserRolePermissionsResponse(
                user_id=user_id,
                permissions=permission_responses,
                effective_operations=effective_operations,
                can_create_shares=can_create_shares,
                can_manage_permissions=can_manage_permissions,
                can_view_analytics=can_view_analytics
            )

        except Exception as e:
            logger.error(
                "Failed to get user permissions",
                user_id=user_id,
                error=str(e)
            )
            raise

    async def revoke_role_permission(
        self,
        permission_id: UUID,
        revoked_by: str,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """Revoke a role permission."""
        if db is None:
            db = await get_database()

        try:
            # Get the permission
            result = await db.execute(
                select(ShareRolePermissions).where(ShareRolePermissions.permission_id == permission_id)
            )
            permission = result.scalar_one_or_none()

            if not permission:
                raise RolePermissionError("Permission not found")

            # Check if requester has permission to revoke
            has_permission = await self.check_permission(
                revoked_by, ShareOperation.MANAGE_PERMISSIONS, permission.scope, permission.scope_id, db
            )
            
            if not has_permission.has_permission:
                raise InsufficientPermissionError("Insufficient permissions to revoke roles")

            # Deactivate the permission
            permission.active = False
            permission.updated_at = datetime.now(timezone.utc)

            await db.commit()

            logger.info(
                "Role permission revoked",
                permission_id=str(permission_id),
                user_id=permission.user_id,
                role=permission.role.value,
                revoked_by=revoked_by
            )

            return True

        except Exception as e:
            await db.rollback()
            logger.error(
                "Failed to revoke role permission",
                permission_id=str(permission_id),
                error=str(e)
            )
            raise

    async def get_permission_matrix(self) -> List[SharePermissionMatrix]:
        """Get permission matrix for all roles."""
        matrix = []
        
        for role, config in self.DEFAULT_ROLE_PERMISSIONS.items():
            permissions = {}
            for operation in ShareOperation:
                permissions[operation] = {}
                for scope in PermissionScope:
                    # Check if operation is allowed for this role
                    has_op = operation.value in config["operations"]
                    # Check if scope is allowed for this role
                    has_scope = scope.value in config["scopes"]
                    permissions[operation][scope] = has_op and has_scope

            # Define typical use cases
            use_cases = {
                ShareRole.ADMIN: [
                    "System administrators",
                    "Platform managers",
                    "Security officers"
                ],
                ShareRole.MANAGER: [
                    "Department managers",
                    "Team leads",
                    "Project managers"
                ],
                ShareRole.CREATOR: [
                    "Content creators",
                    "Report authors",
                    "Dashboard developers"
                ],
                ShareRole.MEMBER: [
                    "Team members",
                    "Regular users",
                    "Collaborators"
                ],
                ShareRole.VIEWER: [
                    "Stakeholders",
                    "External users",
                    "Read-only access"
                ]
            }

            matrix.append(SharePermissionMatrix(
                role=role,
                permissions=permissions,
                description=config["description"],
                typical_use_cases=use_cases.get(role, [])
            ))

        # Sort by priority
        matrix.sort(key=lambda x: self.DEFAULT_ROLE_PERMISSIONS[x.role]["priority"], reverse=True)
        return matrix

    async def _permission_matches(
        self,
        permission: ShareRolePermissions,
        operation: ShareOperation,
        scope: PermissionScope,
        scope_id: Optional[str],
        resource_type: Optional[ShareType]
    ) -> bool:
        """Check if a permission matches the requested operation and scope."""
        # Check if operation is allowed
        if operation.value not in permission.operations:
            return False

        # Check scope hierarchy
        if permission.scope == PermissionScope.GLOBAL:
            return True
        elif permission.scope == PermissionScope.RESOURCE_TYPE:
            if scope in [PermissionScope.RESOURCE_TYPE, PermissionScope.RESOURCE, PermissionScope.SHARE]:
                # Check if resource type matches
                if resource_type and permission.resource_types:
                    return resource_type.value in permission.resource_types
                return True
        elif permission.scope == PermissionScope.RESOURCE:
            if scope in [PermissionScope.RESOURCE, PermissionScope.SHARE]:
                return permission.scope_id == scope_id
        elif permission.scope == PermissionScope.SHARE:
            return permission.scope_id == scope_id

        return False

    async def _get_role_definition(
        self,
        role: ShareRole,
        db: AsyncSession
    ) -> Optional[ShareRoleDefinitions]:
        """Get role definition from database."""
        result = await db.execute(
            select(ShareRoleDefinitions).where(ShareRoleDefinitions.role == role)
        )
        return result.scalar_one_or_none()

    async def _log_permission_audit(
        self,
        user_id: str,
        operation: ShareOperation,
        scope: PermissionScope,
        scope_id: Optional[str] = None,
        resource_type: Optional[ShareType] = None,
        share_id: Optional[UUID] = None,
        permission_granted: bool = False,
        granted_by_role: Optional[ShareRole] = None,
        granted_by_permission_id: Optional[UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> None:
        """Log permission audit entry."""
        if db is None:
            db = await get_database()

        try:
            audit_log = SharePermissionAuditLog(
                log_id=uuid4(),
                user_id=user_id,
                operation=operation,
                scope=scope,
                scope_id=scope_id,
                resource_type=resource_type,
                share_id=share_id,
                permission_granted=permission_granted,
                granted_by_role=granted_by_role,
                granted_by_permission_id=granted_by_permission_id,
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id
            )

            db.add(audit_log)
            await db.commit()

            # Also log to comprehensive audit trail
            try:
                from app.services.audit_trail_service import audit_trail_service
                from app.models.sharing_models import AuditEventType, AuditEventSeverity
                
                # Determine event type and severity based on permission result
                if permission_granted:
                    event_type = AuditEventType.PERMISSION_GRANTED
                    severity = AuditEventSeverity.LOW
                    title = "Permission Granted"
                    description = f"User granted {operation.value} permission for {scope.value}"
                else:
                    event_type = AuditEventType.PERMISSION_DENIED
                    severity = AuditEventSeverity.MEDIUM
                    title = "Permission Denied"
                    description = f"User denied {operation.value} permission for {scope.value}"
                
                await audit_trail_service.log_permission_event(
                    event_type=event_type,
                    title=title,
                    description=description,
                    user_id=user_id,
                    operation=operation,
                    scope=scope,
                    scope_id=scope_id,
                    authorization_granted=permission_granted,
                    severity=severity,
                    context={
                        "resource_type": resource_type.value if resource_type else None,
                        "share_id": str(share_id) if share_id else None,
                        "granted_by_role": granted_by_role.value if granted_by_role else None,
                        "granted_by_permission_id": str(granted_by_permission_id) if granted_by_permission_id else None
                    },
                    ip_address=ip_address,
                    db=db
                )
            except Exception as audit_error:
                logger.warning(
                    "Failed to log to comprehensive audit trail",
                    user_id=user_id,
                    operation=operation.value,
                    error=str(audit_error)
                )

        except Exception as e:
            logger.error(
                "Failed to log permission audit",
                user_id=user_id,
                operation=operation.value,
                error=str(e)
            )


# Service instance
role_permission_service = RolePermissionService()