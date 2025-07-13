"""
Authentication endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis
from typing import Dict, Any

from ....core.config import settings
from ....core.logging import get_logger
from ....core.exceptions import (
    AuthenticationError,
    ValidationError,
    ServiceError,
    map_exception_to_http
)
from ....models.auth import (
    UserLogin,
    UserRegister,
    RefreshTokenRequest,
    ChangePasswordRequest,
    LoginResponse,
    LogoutResponse,
    TokenResponse,
    UserProfile,
    PasswordStrengthResponse,
    AuthStatusResponse
)
from ....models.user import User
from ....services.auth_service import auth_service
from ....api.deps import (
    get_async_session,
    get_redis,
    get_current_user,
    get_current_user_optional,
    security
)

logger = get_logger(__name__)
router = APIRouter()


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(
    request: Request,
    login_data: UserLogin,
    db: AsyncSession = Depends(get_async_session),
    redis_client: redis.Redis = Depends(get_redis)
):
    """
    User login endpoint
    
    Authenticates user credentials and returns JWT tokens with session information.
    """
    try:
        result = await auth_service.login_user(db, redis_client, request, login_data)
        
        logger.info(
            "Login endpoint accessed",
            username=login_data.email,
            success=True,
            ip_address=request.client.host if request.client else None
        )
        
        return result
        
    except (AuthenticationError, ValidationError, ServiceError) as e:
        logger.warning(
            "Login failed",
            username=login_data.email,
            error=str(e),
            ip_address=request.client.host if request.client else None
        )
        raise map_exception_to_http(e)


@router.post("/logout", response_model=LogoutResponse, status_code=status.HTTP_200_OK)
async def logout(
    current_user: User = Depends(get_current_user),
    redis_client: redis.Redis = Depends(get_redis)
):
    """
    User logout endpoint
    
    Revokes user session and invalidates tokens.
    """
    try:
        result = await auth_service.logout_user(redis_client, current_user)
        
        logger.info(
            "Logout endpoint accessed",
            user_id=str(current_user.id),
            username=current_user.username
        )
        
        return LogoutResponse(**result)
        
    except ServiceError as e:
        logger.error(
            "Logout failed",
            user_id=str(current_user.id),
            error=str(e)
        )
        raise map_exception_to_http(e)


@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def refresh_tokens(
    refresh_request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_async_session),
    redis_client: redis.Redis = Depends(get_redis)
):
    """
    Token refresh endpoint
    
    Refreshes access token using valid refresh token.
    """
    try:
        result = await auth_service.refresh_tokens(
            db, redis_client, refresh_request.refresh_token
        )
        
        logger.info("Token refresh successful")
        return result
        
    except (AuthenticationError, ServiceError) as e:
        logger.warning("Token refresh failed", error=str(e))
        raise map_exception_to_http(e)


@router.post("/register", response_model=UserProfile, status_code=status.HTTP_201_CREATED)
async def register(
    registration_data: UserRegister,
    db: AsyncSession = Depends(get_async_session)
):
    """
    User registration endpoint
    
    Creates new user account with validation.
    Note: Registration may be disabled in production environments.
    """
    if not settings.registration_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User registration is disabled"
        )
    
    try:
        user = await auth_service.register_user(db, registration_data)
        user_profile = UserProfile.from_orm(user)
        
        logger.info(
            "User registration successful",
            user_id=str(user.id),
            username=user.username,
            email=user.email
        )
        
        return user_profile
        
    except (ValidationError, ServiceError) as e:
        logger.warning(
            "User registration failed",
            username=registration_data.username,
            email=registration_data.email,
            error=str(e)
        )
        raise map_exception_to_http(e)


@router.get("/me", response_model=UserProfile, status_code=status.HTTP_200_OK)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user profile
    
    Returns authenticated user's profile information.
    """
    return UserProfile.from_orm(current_user)


@router.get("/status", response_model=AuthStatusResponse, status_code=status.HTTP_200_OK)
async def get_auth_status(
    current_user: User = Depends(get_current_user_optional),
    redis_client: redis.Redis = Depends(get_redis)
):
    """
    Get authentication status
    
    Returns current authentication status and user information if authenticated.
    """
    if not current_user:
        return AuthStatusResponse(
            authenticated=False,
            user=None,
            permissions=[],
            session_expires_at=None
        )
    
    # Get session expiration
    session_expires_at = None
    try:
        session_key = f"session:{current_user.id}"
        ttl = await redis_client.ttl(session_key)
        if ttl > 0:
            from datetime import datetime, timedelta
            session_expires_at = datetime.utcnow() + timedelta(seconds=ttl)
    except Exception:
        pass
    
    return AuthStatusResponse(
        authenticated=True,
        user=UserProfile.from_orm(current_user),
        permissions=list(current_user.permissions.keys()) if current_user.permissions else [],
        session_expires_at=session_expires_at
    )


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    redis_client: redis.Redis = Depends(get_redis)
):
    """
    Change user password
    
    Updates user password after validating current password.
    """
    try:
        # Verify current password
        if not auth_service.security_manager.verify_password(
            password_data.current_password, 
            current_user.password_hash
        ):
            raise AuthenticationError("Current password is incorrect")
        
        # Validate new password strength
        validation = await auth_service.validate_password_strength(password_data.new_password)
        if not validation.is_valid:
            raise ValidationError(f"Password validation failed: {', '.join(validation.errors)}")
        
        # Hash new password
        new_password_hash = auth_service.security_manager.get_password_hash(
            password_data.new_password
        )
        
        # Update password in database
        from sqlalchemy import update
        await db.execute(
            update(User)
            .where(User.id == current_user.id)
            .values(password_hash=new_password_hash)
        )
        await db.commit()
        
        # Logout user to force re-authentication
        await auth_service.logout_user(redis_client, current_user)
        
        logger.info(
            "Password changed successfully",
            user_id=str(current_user.id),
            username=current_user.username
        )
        
        return {"message": "Password changed successfully. Please log in again."}
        
    except (AuthenticationError, ValidationError) as e:
        logger.warning(
            "Password change failed",
            user_id=str(current_user.id),
            error=str(e)
        )
        raise map_exception_to_http(e)
    except Exception as e:
        logger.error(
            "Password change error",
            user_id=str(current_user.id),
            error=str(e),
            exc_info=True
        )
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )


@router.post("/validate-password", response_model=PasswordStrengthResponse)
async def validate_password(
    password: Dict[str, str]
):
    """
    Validate password strength
    
    Returns password strength analysis and validation results.
    """
    try:
        result = await auth_service.validate_password_strength(password["password"])
        return result
        
    except Exception as e:
        logger.error("Password validation error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password validation failed"
        )


@router.get("/sessions")
async def get_user_sessions(
    current_user: User = Depends(get_current_user),
    redis_client: redis.Redis = Depends(get_redis)
):
    """
    Get user session information
    
    Returns information about user's active sessions.
    """
    try:
        sessions = await auth_service.get_user_sessions(redis_client, current_user)
        return sessions
        
    except Exception as e:
        logger.error(
            "Get sessions error",
            user_id=str(current_user.id),
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve session information"
        )


@router.delete("/sessions", status_code=status.HTTP_200_OK)
async def revoke_all_sessions(
    current_user: User = Depends(get_current_user),
    redis_client: redis.Redis = Depends(get_redis)
):
    """
    Revoke all user sessions
    
    Logs out user from all devices and invalidates all tokens.
    """
    try:
        result = await auth_service.logout_user(redis_client, current_user)
        
        logger.info(
            "All sessions revoked",
            user_id=str(current_user.id),
            username=current_user.username
        )
        
        return {"message": "All sessions revoked successfully"}
        
    except Exception as e:
        logger.error(
            "Session revocation error",
            user_id=str(current_user.id),
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke sessions"
        )