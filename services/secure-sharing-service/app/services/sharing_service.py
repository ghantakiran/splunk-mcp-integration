"""
Secure sharing service implementing share creation, access validation, and expiration management.
"""

import secrets
import string
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID, uuid4
import hashlib
import bcrypt

from sqlalchemy import select, and_, or_, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_database, SharedResource, ShareAccessLog, ShareInvitation, ShareMetrics
from app.models.sharing_models import (
    CreateShareRequest, UpdateShareRequest, AccessShareRequest, ShareListRequest,
    ShareResponse, ShareAccessResponse, ShareStatsResponse, ExpirationCheckResult,
    ShareSecurityValidation, ShareType, ShareStatus, SharePermission, ExpirationPolicy,
    AccessMethod, ShareOperation, PermissionScope
)
from app.core.config import settings
import structlog

logger = structlog.get_logger(__name__)


class ShareSecurityError(Exception):
    """Exception raised for security-related share access issues."""
    pass


class ShareExpirationError(Exception):
    """Exception raised when share has expired."""
    pass


class ShareNotFoundError(Exception):
    """Exception raised when share is not found."""
    pass


class SharingService:
    """Service for managing secure resource sharing."""

    @staticmethod
    def generate_share_token(length: int = 32) -> str:
        """Generate a secure random share token."""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    @staticmethod
    def generate_invitation_token(length: int = 64) -> str:
        """Generate a secure random invitation token."""
        return secrets.token_urlsafe(length)

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify a password against its hash."""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

    @staticmethod
    def generate_share_url(share_token: str) -> str:
        """Generate the public URL for accessing a share."""
        base_url = getattr(settings, 'SHARE_BASE_URL', 'http://localhost:8016')
        return f"{base_url}/share/{share_token}"

    async def create_share(
        self,
        request: CreateShareRequest,
        user_id: str,
        db: Optional[AsyncSession] = None
    ) -> ShareResponse:
        """Create a new secure share."""
        if db is None:
            db = await get_database()

        try:
            # Check if user has permission to create shares
            from app.services.role_permission_service import role_permission_service
            permission_check = await role_permission_service.check_permission(
                user_id, ShareOperation.CREATE, PermissionScope.RESOURCE_TYPE, 
                resource_type=request.resource_type, db=db
            )
            
            if not permission_check.has_permission:
                raise ShareSecurityError(f"Insufficient permissions to create {request.resource_type.value} shares")
            # Generate unique share token
            share_token = self.generate_share_token()
            
            # Ensure token uniqueness
            while await self._token_exists(share_token, db):
                share_token = self.generate_share_token()

            # Hash password if provided
            password_hash = None
            if request.password_protected and request.password:
                password_hash = self.hash_password(request.password)

            # Create share record
            share = SharedResource(
                share_id=uuid4(),
                resource_type=request.resource_type,
                resource_id=request.resource_id,
                resource_name=request.resource_name,
                share_token=share_token,
                permissions=[perm.value for perm in request.permissions],
                access_method=request.access_method,
                requires_authentication=request.requires_authentication,
                expiration_policy=request.expiration_policy,
                expires_at=request.expires_at,
                max_views=request.max_views,
                max_downloads=request.max_downloads,
                password_protected=request.password_protected,
                password_hash=password_hash,
                allowed_domains=request.allowed_domains,
                allowed_users=request.allowed_users,
                description=request.description,
                custom_message=request.custom_message,
                branding_enabled=request.branding_enabled,
                notify_on_access=request.notify_on_access,
                notify_on_expiration=request.notify_on_expiration,
                notification_emails=request.notification_emails,
                created_by=user_id,
                metadata=request.metadata,
                tags=request.tags
            )

            db.add(share)
            await db.commit()
            await db.refresh(share)

            logger.info(
                "Share created successfully",
                share_id=str(share.share_id),
                resource_type=request.resource_type.value,
                created_by=user_id
            )

            return ShareResponse(
                share_id=share.share_id,
                resource_type=share.resource_type,
                resource_id=share.resource_id,
                resource_name=share.resource_name,
                share_token=share.share_token,
                share_url=self.generate_share_url(share.share_token),
                permissions=[SharePermission(p) for p in share.permissions],
                access_method=share.access_method,
                requires_authentication=share.requires_authentication,
                expiration_policy=share.expiration_policy,
                expires_at=share.expires_at,
                max_views=share.max_views,
                max_downloads=share.max_downloads,
                password_protected=share.password_protected,
                allowed_domains=share.allowed_domains,
                allowed_users=share.allowed_users,
                description=share.description,
                custom_message=share.custom_message,
                branding_enabled=share.branding_enabled,
                status=share.status,
                total_views=share.total_views,
                total_downloads=share.total_downloads,
                unique_viewers=share.unique_viewers,
                created_by=share.created_by,
                created_at=share.created_at,
                updated_at=share.updated_at,
                last_accessed_at=share.last_accessed_at,
                metadata=share.metadata,
                tags=share.tags
            )

        except Exception as e:
            await db.rollback()
            logger.error(
                "Failed to create share",
                error=str(e),
                resource_type=request.resource_type.value,
                created_by=user_id
            )
            raise

    async def access_share(
        self,
        request: AccessShareRequest,
        db: Optional[AsyncSession] = None
    ) -> ShareAccessResponse:
        """Access a shared resource with security validation."""
        if db is None:
            db = await get_database()

        # Get share by token
        share = await self._get_share_by_token(request.share_token, db)
        if not share:
            raise ShareNotFoundError("Share not found")

        # Check expiration
        expiration_result = await self.check_expiration(share.share_id, db)
        if expiration_result.is_expired:
            raise ShareExpirationError(f"Share expired: {expiration_result.expiration_reason}")

        # Validate security
        security_validation = await self._validate_security(share, request)
        if not security_validation.is_valid:
            raise ShareSecurityError(security_validation.error_message)

        # Log access attempt
        await self._log_access(
            share=share,
            request=request,
            action="view",
            success=True,
            db=db
        )

        # Update share metrics
        await self._update_share_metrics(share, request.user_email, db)

        # Collect real-time metrics for analytics
        try:
            from app.services.metrics_collector import metrics_collector
            await metrics_collector.collect_share_interaction_metrics(
                share_id=str(share.share_id),
                action="view",
                user_email=request.user_email,
                ip_address=request.ip_address,
                user_agent=request.user_agent
            )
        except Exception as e:
            # Don't fail the main operation if metrics collection fails
            logger.warning(
                "Failed to collect interaction metrics",
                share_id=str(share.share_id),
                error=str(e)
            )

        # Get resource data (this would integrate with other services)
        resource_data = await self._get_resource_data(share)

        # Calculate remaining limits
        remaining_views = None
        remaining_downloads = None
        if share.max_views:
            remaining_views = max(0, share.max_views - share.total_views)
        if share.max_downloads:
            remaining_downloads = max(0, share.max_downloads - share.total_downloads)

        return ShareAccessResponse(
            success=True,
            share_id=share.share_id,
            resource_type=share.resource_type,
            resource_id=share.resource_id,
            resource_name=share.resource_name,
            permissions=[SharePermission(p) for p in share.permissions],
            resource_data=resource_data,
            custom_message=share.custom_message,
            branding_enabled=share.branding_enabled,
            access_count=share.total_views,
            remaining_views=remaining_views,
            remaining_downloads=remaining_downloads,
            expires_at=share.expires_at
        )

    async def check_expiration(
        self,
        share_id: UUID,
        db: Optional[AsyncSession] = None
    ) -> ExpirationCheckResult:
        """Check if a share has expired."""
        if db is None:
            db = await get_database()

        result = await db.execute(
            select(SharedResource).where(SharedResource.share_id == share_id)
        )
        share = result.scalar_one_or_none()
        
        if not share:
            return ExpirationCheckResult(
                is_expired=True,
                expiration_reason="Share not found"
            )

        now = datetime.now(timezone.utc)
        
        # Check time-based expiration
        if share.expiration_policy in [ExpirationPolicy.AFTER_TIME, ExpirationPolicy.COMBINED]:
            if share.expires_at and now >= share.expires_at:
                return ExpirationCheckResult(
                    is_expired=True,
                    expiration_reason="Time limit exceeded",
                    expires_at=share.expires_at
                )

        # Check view-based expiration
        if share.expiration_policy in [ExpirationPolicy.AFTER_VIEWS, ExpirationPolicy.COMBINED]:
            if share.max_views and share.total_views >= share.max_views:
                return ExpirationCheckResult(
                    is_expired=True,
                    expiration_reason="View limit exceeded",
                    remaining_views=0
                )

        # Check download-based expiration
        if share.expiration_policy in [ExpirationPolicy.AFTER_DOWNLOADS, ExpirationPolicy.COMBINED]:
            if share.max_downloads and share.total_downloads >= share.max_downloads:
                return ExpirationCheckResult(
                    is_expired=True,
                    expiration_reason="Download limit exceeded",
                    remaining_downloads=0
                )

        # Calculate remaining time
        time_until_expiration = None
        if share.expires_at:
            time_until_expiration = (share.expires_at - now).total_seconds()

        # Calculate remaining limits
        remaining_views = None
        remaining_downloads = None
        if share.max_views:
            remaining_views = max(0, share.max_views - share.total_views)
        if share.max_downloads:
            remaining_downloads = max(0, share.max_downloads - share.total_downloads)

        return ExpirationCheckResult(
            is_expired=False,
            expires_at=share.expires_at,
            remaining_views=remaining_views,
            remaining_downloads=remaining_downloads,
            time_until_expiration=time_until_expiration
        )

    async def list_shares(
        self,
        request: ShareListRequest,
        user_id: str,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """List shares with filtering and pagination."""
        if db is None:
            db = await get_database()

        # Check if user has permission to list shares
        from app.services.role_permission_service import role_permission_service
        
        # Check if user has global read permissions (can see all shares)
        global_permission_check = await role_permission_service.check_permission(
            user_id, ShareOperation.READ, PermissionScope.GLOBAL, db=db
        )
        
        # Build query - either user's own shares or all shares if they have global permissions
        if global_permission_check.has_permission:
            # User can see all shares
            query = select(SharedResource)
        else:
            # Check if user has resource-type level permissions
            resource_type_permission = False
            if request.resource_type:
                resource_type_check = await role_permission_service.check_permission(
                    user_id, ShareOperation.READ, PermissionScope.RESOURCE_TYPE,
                    resource_type=request.resource_type, db=db
                )
                resource_type_permission = resource_type_check.has_permission
            
            if resource_type_permission:
                # User can see shares of specific resource type
                query = select(SharedResource)
                if request.resource_type:
                    query = query.where(SharedResource.resource_type == request.resource_type)
            else:
                # User can only see their own shares
                query = select(SharedResource).where(SharedResource.created_by == user_id)

        # Apply filters
        if request.resource_type:
            query = query.where(SharedResource.resource_type == request.resource_type)
        
        if request.status:
            query = query.where(SharedResource.status == request.status)
        
        if request.created_after:
            query = query.where(SharedResource.created_at >= request.created_after)
        
        if request.created_before:
            query = query.where(SharedResource.created_at <= request.created_before)
        
        if request.expires_after:
            query = query.where(SharedResource.expires_at >= request.expires_after)
        
        if request.expires_before:
            query = query.where(SharedResource.expires_at <= request.expires_before)
        
        if request.tags:
            for tag in request.tags:
                query = query.where(SharedResource.tags.contains([tag]))
        
        if request.search:
            search_term = f"%{request.search}%"
            query = query.where(
                or_(
                    SharedResource.resource_name.ilike(search_term),
                    SharedResource.description.ilike(search_term)
                )
            )

        # Get total count
        count_result = await db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar()

        # Apply pagination
        query = query.offset(request.offset).limit(request.limit)
        
        # Execute query
        result = await db.execute(query)
        shares = result.scalars().all()

        # Convert to response models
        share_responses = []
        for share in shares:
            share_responses.append(ShareResponse(
                share_id=share.share_id,
                resource_type=share.resource_type,
                resource_id=share.resource_id,
                resource_name=share.resource_name,
                share_token=share.share_token,
                share_url=self.generate_share_url(share.share_token),
                permissions=[SharePermission(p) for p in share.permissions],
                access_method=share.access_method,
                requires_authentication=share.requires_authentication,
                expiration_policy=share.expiration_policy,
                expires_at=share.expires_at,
                max_views=share.max_views,
                max_downloads=share.max_downloads,
                password_protected=share.password_protected,
                allowed_domains=share.allowed_domains,
                allowed_users=share.allowed_users,
                description=share.description,
                custom_message=share.custom_message,
                branding_enabled=share.branding_enabled,
                status=share.status,
                total_views=share.total_views,
                total_downloads=share.total_downloads,
                unique_viewers=share.unique_viewers,
                created_by=share.created_by,
                created_at=share.created_at,
                updated_at=share.updated_at,
                last_accessed_at=share.last_accessed_at,
                metadata=share.metadata,
                tags=share.tags
            ))

        return {
            "items": share_responses,
            "total": total,
            "limit": request.limit,
            "offset": request.offset,
            "has_more": request.offset + len(share_responses) < total
        }

    async def update_share(
        self,
        share_id: UUID,
        request: UpdateShareRequest,
        user_id: str,
        db: Optional[AsyncSession] = None
    ) -> ShareResponse:
        """Update an existing share."""
        if db is None:
            db = await get_database()

        try:
            # Get existing share first
            result = await db.execute(
                select(SharedResource).where(SharedResource.share_id == share_id)
            )
            share = result.scalar_one_or_none()
            
            if not share:
                raise ShareNotFoundError("Share not found")

            # Check if user has permission to update this share
            from app.services.role_permission_service import role_permission_service
            
            # Check if user is the creator or has global/resource update permissions
            is_creator = share.created_by == user_id
            if not is_creator:
                permission_check = await role_permission_service.check_permission(
                    user_id, ShareOperation.UPDATE, PermissionScope.SHARE, 
                    scope_id=str(share_id), db=db
                )
                
                if not permission_check.has_permission:
                    # Try resource-level permission
                    permission_check = await role_permission_service.check_permission(
                        user_id, ShareOperation.UPDATE, PermissionScope.RESOURCE,
                        scope_id=str(share.resource_id), resource_type=share.resource_type, db=db
                    )
                    
                    if not permission_check.has_permission:
                        raise ShareSecurityError("Insufficient permissions to update this share")

            # Update fields
            if request.resource_name is not None:
                share.resource_name = request.resource_name
            if request.permissions is not None:
                share.permissions = [perm.value for perm in request.permissions]
            if request.expires_at is not None:
                share.expires_at = request.expires_at
            if request.max_views is not None:
                share.max_views = request.max_views
            if request.max_downloads is not None:
                share.max_downloads = request.max_downloads
            if request.password_protected is not None:
                share.password_protected = request.password_protected
            if request.password is not None:
                share.password_hash = self.hash_password(request.password)
            if request.description is not None:
                share.description = request.description
            if request.custom_message is not None:
                share.custom_message = request.custom_message
            if request.notify_on_access is not None:
                share.notify_on_access = request.notify_on_access
            if request.notify_on_expiration is not None:
                share.notify_on_expiration = request.notify_on_expiration
            if request.metadata is not None:
                share.metadata = request.metadata
            if request.tags is not None:
                share.tags = request.tags

            await db.commit()
            await db.refresh(share)

            logger.info(
                "Share updated successfully",
                share_id=str(share.share_id),
                updated_by=user_id
            )

            return ShareResponse(
                share_id=share.share_id,
                resource_type=share.resource_type,
                resource_id=share.resource_id,
                resource_name=share.resource_name,
                share_token=share.share_token,
                share_url=self.generate_share_url(share.share_token),
                permissions=[SharePermission(p) for p in share.permissions],
                access_method=share.access_method,
                requires_authentication=share.requires_authentication,
                expiration_policy=share.expiration_policy,
                expires_at=share.expires_at,
                max_views=share.max_views,
                max_downloads=share.max_downloads,
                password_protected=share.password_protected,
                allowed_domains=share.allowed_domains,
                allowed_users=share.allowed_users,
                description=share.description,
                custom_message=share.custom_message,
                branding_enabled=share.branding_enabled,
                status=share.status,
                total_views=share.total_views,
                total_downloads=share.total_downloads,
                unique_viewers=share.unique_viewers,
                created_by=share.created_by,
                created_at=share.created_at,
                updated_at=share.updated_at,
                last_accessed_at=share.last_accessed_at,
                metadata=share.metadata,
                tags=share.tags
            )

        except Exception as e:
            await db.rollback()
            logger.error(
                "Failed to update share",
                share_id=str(share_id),
                error=str(e),
                updated_by=user_id
            )
            raise

    async def delete_share(
        self,
        share_id: UUID,
        user_id: str,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """Delete a share."""
        if db is None:
            db = await get_database()

        try:
            # Get existing share first
            result = await db.execute(
                select(SharedResource).where(SharedResource.share_id == share_id)
            )
            share = result.scalar_one_or_none()
            
            if not share:
                raise ShareNotFoundError("Share not found")

            # Check if user has permission to delete this share
            from app.services.role_permission_service import role_permission_service
            
            # Check if user is the creator or has global/resource delete permissions
            is_creator = share.created_by == user_id
            if not is_creator:
                permission_check = await role_permission_service.check_permission(
                    user_id, ShareOperation.DELETE, PermissionScope.SHARE, 
                    scope_id=str(share_id), db=db
                )
                
                if not permission_check.has_permission:
                    # Try resource-level permission
                    permission_check = await role_permission_service.check_permission(
                        user_id, ShareOperation.DELETE, PermissionScope.RESOURCE,
                        scope_id=str(share.resource_id), resource_type=share.resource_type, db=db
                    )
                    
                    if not permission_check.has_permission:
                        raise ShareSecurityError("Insufficient permissions to delete this share")

            await db.delete(share)
            await db.commit()

            logger.info(
                "Share deleted successfully",
                share_id=str(share_id),
                deleted_by=user_id
            )

            return True

        except Exception as e:
            await db.rollback()
            logger.error(
                "Failed to delete share",
                share_id=str(share_id),
                error=str(e),
                deleted_by=user_id
            )
            raise

    async def _token_exists(self, token: str, db: AsyncSession) -> bool:
        """Check if a share token already exists."""
        result = await db.execute(
            select(SharedResource.share_id).where(SharedResource.share_token == token)
        )
        return result.scalar_one_or_none() is not None

    async def _get_share_by_token(
        self,
        token: str,
        db: AsyncSession
    ) -> Optional[SharedResource]:
        """Get share by token."""
        result = await db.execute(
            select(SharedResource).where(SharedResource.share_token == token)
        )
        return result.scalar_one_or_none()

    async def _validate_security(
        self,
        share: SharedResource,
        request: AccessShareRequest
    ) -> ShareSecurityValidation:
        """Validate security requirements for share access."""
        warnings = []

        # Check if share is active
        if share.status != ShareStatus.ACTIVE:
            return ShareSecurityValidation(
                is_valid=False,
                has_access=False,
                error_message=f"Share is {share.status.value}"
            )

        # Check authentication requirements
        if share.requires_authentication:
            if not request.user_email:
                return ShareSecurityValidation(
                    is_valid=False,
                    has_access=False,
                    error_message="Authentication required - user email must be provided"
                )
            
            # Validate email format for authenticated access
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, request.user_email):
                return ShareSecurityValidation(
                    is_valid=False,
                    has_access=False,
                    error_message="Invalid email format for authenticated access"
                )
        elif not share.requires_authentication:
            # For public shares, add warning if user tries to provide credentials
            if request.user_email:
                warnings.append("Email provided but not required for public share")

        # Check password protection
        requires_password = share.password_protected
        if requires_password:
            if not request.password:
                return ShareSecurityValidation(
                    is_valid=False,
                    has_access=False,
                    requires_password=True,
                    error_message="Password required"
                )
            
            if not self.verify_password(request.password, share.password_hash):
                return ShareSecurityValidation(
                    is_valid=False,
                    has_access=False,
                    requires_password=True,
                    error_message="Invalid password"
                )

        # Check domain restrictions
        domain_allowed = True
        if share.allowed_domains and request.user_email:
            user_domain = request.user_email.split('@')[-1] if '@' in request.user_email else None
            domain_allowed = user_domain and user_domain in share.allowed_domains
            
            if not domain_allowed:
                return ShareSecurityValidation(
                    is_valid=False,
                    has_access=False,
                    domain_allowed=False,
                    error_message="Domain not allowed"
                )

        # Check user allowlist
        user_allowed = True
        if share.allowed_users and request.user_email:
            user_allowed = request.user_email in share.allowed_users
            
            if not user_allowed:
                return ShareSecurityValidation(
                    is_valid=False,
                    has_access=False,
                    user_allowed=False,
                    error_message="User not allowed"
                )

        return ShareSecurityValidation(
            is_valid=True,
            has_access=True,
            requires_password=requires_password,
            domain_allowed=domain_allowed,
            user_allowed=user_allowed,
            warnings=warnings
        )

    async def _log_access(
        self,
        share: SharedResource,
        request: AccessShareRequest,
        action: str,
        success: bool,
        error_message: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> None:
        """Log share access attempt."""
        if db is None:
            db = await get_database()

        access_log = ShareAccessLog(
            log_id=uuid4(),
            share_id=share.share_id,
            user_email=request.user_email,
            ip_address=request.ip_address,
            user_agent=request.user_agent,
            referrer=request.referrer,
            action=action,
            success=success,
            error_message=error_message
        )

        db.add(access_log)
        await db.commit()

    async def _update_share_metrics(
        self,
        share: SharedResource,
        user_email: Optional[str],
        db: AsyncSession
    ) -> None:
        """Update share access metrics."""
        # Update view count
        share.total_views += 1
        share.last_accessed_at = datetime.now(timezone.utc)

        # Update unique viewers count
        if user_email:
            # Check if this is a new viewer
            result = await db.execute(
                select(func.count(ShareAccessLog.log_id.distinct())).where(
                    and_(
                        ShareAccessLog.share_id == share.share_id,
                        ShareAccessLog.user_email == user_email,
                        ShareAccessLog.success == True
                    )
                )
            )
            access_count = result.scalar() or 0
            
            if access_count == 0:  # First successful access by this user
                share.unique_viewers += 1

        await db.commit()

    async def _get_resource_data(self, share: SharedResource) -> Optional[Dict[str, Any]]:
        """Get resource data (placeholder for service integration)."""
        # This would integrate with other services to fetch the actual resource data
        # For now, return basic metadata
        return {
            "resource_type": share.resource_type.value,
            "resource_id": str(share.resource_id),
            "resource_name": share.resource_name,
            "last_updated": share.updated_at.isoformat() if share.updated_at else None
        }


# Service instance
sharing_service = SharingService()