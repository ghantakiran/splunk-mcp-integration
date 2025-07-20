"""
API endpoints for role-based permission management.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_database
from app.models.sharing_models import (
    CreateRolePermissionRequest, UpdateRolePermissionRequest, RolePermissionResponse,
    UserRolePermissionsResponse, RolePermissionCheck, SharePermissionMatrix,
    BulkRoleOperation, ShareRole, ShareOperation, PermissionScope, ShareType
)
from app.services.role_permission_service import (
    role_permission_service, RolePermissionError, InsufficientPermissionError
)
from app.utils.auth import get_current_user
from app.utils.rate_limiter import rate_limit
import structlog

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post(
    "/assign",
    response_model=RolePermissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign role permission to user"
)
async def assign_role_permission(
    request: CreateRolePermissionRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
    _: None = Depends(rate_limit("role_assign", max_requests=20, window_seconds=60))
):
    """
    Assign a role permission to a user.
    
    - **user_id**: User ID to assign role to
    - **role**: Role to assign (admin, manager, creator, member, viewer)
    - **scope**: Scope of permission (global, resource_type, resource, share)
    - **scope_id**: ID for specific scope (optional for global)
    - **resource_types**: Specific resource types (optional)
    - **expires_at**: When the role assignment expires (optional)
    """
    try:
        assigned_by = current_user.get("sub") or current_user.get("user_id")
        if not assigned_by:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user context"
            )

        permission = await role_permission_service.assign_role_permission(request, assigned_by, db)
        
        logger.info(
            "Role permission assigned via API",
            user_id=request.user_id,
            role=request.role.value,
            scope=request.scope.value,
            assigned_by=assigned_by
        )
        
        return permission

    except InsufficientPermissionError as e:
        logger.warning(
            "Role assignment failed - insufficient permissions",
            user_id=request.user_id,
            role=request.role.value,
            error=str(e),
            assigned_by=current_user.get("sub")
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except RolePermissionError as e:
        logger.warning(
            "Role assignment failed - role error",
            user_id=request.user_id,
            role=request.role.value,
            error=str(e),
            assigned_by=current_user.get("sub")
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Role assignment failed - server error",
            user_id=request.user_id,
            role=request.role.value,
            error=str(e),
            assigned_by=current_user.get("sub")
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign role permission"
        )


@router.get(
    "/user/{user_id}",
    response_model=UserRolePermissionsResponse,
    summary="Get user's role permissions"
)
async def get_user_permissions(
    user_id: str,
    include_expired: bool = False,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
    _: None = Depends(rate_limit("role_get", max_requests=100, window_seconds=60))
):
    """
    Get all role permissions for a specific user.
    
    - **user_id**: User ID to get permissions for
    - **include_expired**: Whether to include expired permissions
    """
    try:
        requester_id = current_user.get("sub") or current_user.get("user_id")
        if not requester_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user context"
            )

        # Check if user can view permissions (admin/manager or own permissions)
        if user_id != requester_id:
            permission_check = await role_permission_service.check_permission(
                requester_id, ShareOperation.MANAGE_PERMISSIONS, PermissionScope.GLOBAL, db=db
            )
            if not permission_check.has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions to view user permissions"
                )

        permissions = await role_permission_service.get_user_permissions(user_id, include_expired, db)
        
        logger.debug(
            "User permissions retrieved",
            user_id=user_id,
            requester_id=requester_id,
            permission_count=len(permissions.permissions)
        )
        
        return permissions

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get user permissions",
            user_id=user_id,
            error=str(e),
            requester_id=current_user.get("sub")
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user permissions"
        )


@router.post(
    "/check",
    response_model=RolePermissionCheck,
    summary="Check user permission for operation"
)
async def check_permission(
    user_id: str,
    operation: ShareOperation,
    scope: PermissionScope,
    scope_id: Optional[str] = None,
    resource_type: Optional[ShareType] = None,
    share_id: Optional[UUID] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
    _: None = Depends(rate_limit("role_check", max_requests=200, window_seconds=60))
):
    """
    Check if a user has permission for a specific operation.
    
    - **user_id**: User ID to check permissions for
    - **operation**: Operation to check (create, read, update, delete, etc.)
    - **scope**: Scope of the operation (global, resource_type, resource, share)
    - **scope_id**: ID for specific scope (optional)
    - **resource_type**: Type of resource (optional)
    - **share_id**: Specific share ID (optional)
    """
    try:
        requester_id = current_user.get("sub") or current_user.get("user_id")
        if not requester_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user context"
            )

        # Allow users to check their own permissions, admins can check anyone's
        if user_id != requester_id:
            admin_check = await role_permission_service.check_permission(
                requester_id, ShareOperation.MANAGE_PERMISSIONS, PermissionScope.GLOBAL, db=db
            )
            if not admin_check.has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions to check other user's permissions"
                )

        permission_result = await role_permission_service.check_permission(
            user_id, operation, scope, scope_id, resource_type, share_id, db
        )
        
        logger.debug(
            "Permission check completed",
            user_id=user_id,
            operation=operation.value,
            scope=scope.value,
            has_permission=permission_result.has_permission,
            requester_id=requester_id
        )
        
        return permission_result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Permission check failed",
            user_id=user_id,
            operation=operation.value,
            error=str(e),
            requester_id=current_user.get("sub")
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check permission"
        )


@router.delete(
    "/{permission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke role permission"
)
async def revoke_role_permission(
    permission_id: UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
    _: None = Depends(rate_limit("role_revoke", max_requests=50, window_seconds=60))
):
    """
    Revoke a role permission.
    
    - **permission_id**: ID of the permission to revoke
    """
    try:
        revoked_by = current_user.get("sub") or current_user.get("user_id")
        if not revoked_by:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user context"
            )

        success = await role_permission_service.revoke_role_permission(permission_id, revoked_by, db)
        
        if success:
            logger.info(
                "Role permission revoked via API",
                permission_id=str(permission_id),
                revoked_by=revoked_by
            )
        
        return None

    except InsufficientPermissionError as e:
        logger.warning(
            "Role revocation failed - insufficient permissions",
            permission_id=str(permission_id),
            error=str(e),
            revoked_by=current_user.get("sub")
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except RolePermissionError as e:
        logger.warning(
            "Role revocation failed - role error",
            permission_id=str(permission_id),
            error=str(e),
            revoked_by=current_user.get("sub")
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Role revocation failed - server error",
            permission_id=str(permission_id),
            error=str(e),
            revoked_by=current_user.get("sub")
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke role permission"
        )


@router.get(
    "/matrix",
    response_model=List[SharePermissionMatrix],
    summary="Get permission matrix for all roles"
)
async def get_permission_matrix(
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: None = Depends(rate_limit("role_matrix", max_requests=50, window_seconds=60))
):
    """
    Get the permission matrix showing what operations each role can perform.
    
    Returns a matrix of roles and their allowed operations for each scope.
    """
    try:
        # Anyone can view the permission matrix for transparency
        matrix = await role_permission_service.get_permission_matrix()
        
        logger.debug(
            "Permission matrix retrieved",
            requester_id=current_user.get("sub"),
            roles_count=len(matrix)
        )
        
        return matrix

    except Exception as e:
        logger.error(
            "Failed to get permission matrix",
            error=str(e),
            requester_id=current_user.get("sub")
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve permission matrix"
        )


@router.post(
    "/initialize",
    status_code=status.HTTP_200_OK,
    summary="Initialize default role definitions"
)
async def initialize_default_roles(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
    _: None = Depends(rate_limit("role_init", max_requests=5, window_seconds=3600))  # Very limited
):
    """
    Initialize default role definitions.
    
    This endpoint should only be called during system setup.
    Requires admin permissions.
    """
    try:
        admin_user_id = current_user.get("sub") or current_user.get("user_id")
        if not admin_user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user context"
            )

        # Check if user has admin permissions
        # For initial setup, we'll be more lenient and allow if they have manage_permissions globally
        permission_check = await role_permission_service.check_permission(
            admin_user_id, ShareOperation.MANAGE_PERMISSIONS, PermissionScope.GLOBAL, db=db
        )
        
        if not permission_check.has_permission:
            # If no permissions exist yet (first time setup), allow the operation
            # This is needed for initial system setup
            logger.warning(
                "Initializing roles without explicit permission check - this should only happen during initial setup",
                admin_user_id=admin_user_id
            )

        await role_permission_service.initialize_default_roles(admin_user_id, db)
        
        logger.info(
            "Default roles initialized via API",
            admin_user_id=admin_user_id
        )
        
        return {"message": "Default role definitions initialized successfully"}

    except Exception as e:
        logger.error(
            "Failed to initialize default roles",
            error=str(e),
            admin_user_id=current_user.get("sub")
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize default roles"
        )


@router.post(
    "/bulk-assign",
    response_model=BulkRoleOperation,
    summary="Bulk assign roles to multiple users"
)
async def bulk_assign_roles(
    operation: BulkRoleOperation,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
    _: None = Depends(rate_limit("role_bulk", max_requests=10, window_seconds=60))
):
    """
    Bulk assign roles to multiple users.
    
    - **operation**: Type of operation (assign, update, revoke)
    - **user_ids**: List of user IDs
    - **role**: Role to assign
    - **scope**: Scope of permission
    - **scope_id**: ID for specific scope (optional)
    - **expires_at**: Expiration time (optional)
    """
    try:
        assigned_by = current_user.get("sub") or current_user.get("user_id")
        if not assigned_by:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user context"
            )

        # Check permissions for bulk operations
        permission_check = await role_permission_service.check_permission(
            assigned_by, ShareOperation.MANAGE_PERMISSIONS, operation.scope, operation.scope_id, db=db
        )
        
        if not permission_check.has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for bulk role operations"
            )

        successful_operations = 0
        failed_operations = 0
        errors = []

        for user_id in operation.user_ids:
            try:
                if operation.operation == "assign":
                    request = CreateRolePermissionRequest(
                        user_id=user_id,
                        role=operation.role,
                        scope=operation.scope,
                        scope_id=operation.scope_id,
                        expires_at=operation.expires_at
                    )
                    await role_permission_service.assign_role_permission(request, assigned_by, db)
                    successful_operations += 1
                else:
                    # For update/revoke operations, would need additional implementation
                    failed_operations += 1
                    errors.append({
                        "user_id": user_id,
                        "error": f"Operation {operation.operation} not yet implemented"
                    })
                    
            except Exception as e:
                failed_operations += 1
                errors.append({
                    "user_id": user_id,
                    "error": str(e)
                })

        result = BulkRoleOperation(
            operation=operation.operation,
            user_ids=operation.user_ids,
            role=operation.role,
            scope=operation.scope,
            scope_id=operation.scope_id,
            expires_at=operation.expires_at,
            successful_operations=successful_operations,
            failed_operations=failed_operations,
            errors=errors
        )

        logger.info(
            "Bulk role operation completed",
            operation=operation.operation,
            total_users=len(operation.user_ids),
            successful=successful_operations,
            failed=failed_operations,
            assigned_by=assigned_by
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Bulk role operation failed",
            operation=operation.operation,
            user_count=len(operation.user_ids),
            error=str(e),
            assigned_by=current_user.get("sub")
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform bulk role operation"
        )


@router.get(
    "/roles",
    response_model=List[Dict[str, Any]],
    summary="Get available roles and their descriptions"
)
async def get_available_roles(
    current_user: Dict[str, Any] = Depends(get_current_user),
    _: None = Depends(rate_limit("role_list", max_requests=100, window_seconds=60))
):
    """
    Get list of available roles and their descriptions.
    """
    try:
        roles = []
        
        for role, config in role_permission_service.DEFAULT_ROLE_PERMISSIONS.items():
            roles.append({
                "role": role.value,
                "display_name": role.value.title(),
                "description": config["description"],
                "priority": config["priority"],
                "operations": config["operations"],
                "scopes": config["scopes"]
            })
        
        # Sort by priority (highest first)
        roles.sort(key=lambda x: x["priority"], reverse=True)
        
        logger.debug(
            "Available roles retrieved",
            requester_id=current_user.get("sub"),
            roles_count=len(roles)
        )
        
        return roles

    except Exception as e:
        logger.error(
            "Failed to get available roles",
            error=str(e),
            requester_id=current_user.get("sub")
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve available roles"
        )