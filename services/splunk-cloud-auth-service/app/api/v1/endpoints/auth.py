"""
Authentication endpoints for Splunk Cloud Authentication Service
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional
import logging
from datetime import datetime
import uuid

from app.core.database import get_db
from app.models.auth_models import (
    User,
    AuthSession,
    UserCreate,
    UserLogin,
    UserResponse
)
from app.services.oauth_service import OAuthService

router = APIRouter()
logger = logging.getLogger(__name__)
security = HTTPBearer()

oauth_service = OAuthService()


@router.post("/register", response_model=UserResponse)
async def register_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user"""
    
    try:
        # Check if username or email already exists
        result = await db.execute(
            select(User).where(
                or_(
                    User.username == user_data.username,
                    User.email == user_data.email
                )
            )
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            field = "username" if existing_user.username == user_data.username else "email"
            raise HTTPException(
                status_code=400,
                detail={
                    "error": f"{field}_already_exists",
                    "message": f"User with this {field} already exists"
                }
            )
        
        # Hash password
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        hashed_password = pwd_context.hash(user_data.password)
        
        # Create user
        user = User(
            id=str(uuid.uuid4()),
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            hashed_password=hashed_password,
            tenant_id=user_data.tenant_id,
            is_verified=False,
            password_changed_at=datetime.utcnow()
        )
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"Registered new user: {user.username} ({user.id})")
        
        return UserResponse.from_orm(user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "error": "registration_failed",
                "message": "Failed to register user"
            }
        )


@router.post("/login")
async def login_user(
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """Authenticate user and create session"""
    
    try:
        # Find user
        from sqlalchemy import or_
        result = await db.execute(
            select(User).where(
                and_(
                    or_(
                        User.username == login_data.username,
                        User.email == login_data.username
                    ),
                    User.is_active == True
                )
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "invalid_credentials",
                    "message": "Invalid username or password"
                }
            )
        
        # Check if account is locked
        if user.locked_until and user.locked_until > datetime.utcnow():
            raise HTTPException(
                status_code=423,
                detail={
                    "error": "account_locked",
                    "message": f"Account is locked until {user.locked_until}"
                }
            )
        
        # Verify password
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        if not user.hashed_password or not pwd_context.verify(login_data.password, user.hashed_password):
            # Increment failed login attempts
            user.failed_login_attempts += 1
            
            # Lock account after 5 failed attempts
            if user.failed_login_attempts >= 5:
                from datetime import timedelta
                user.locked_until = datetime.utcnow() + timedelta(minutes=30)
                logger.warning(f"Account locked for user: {user.username}")
            
            await db.commit()
            
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "invalid_credentials",
                    "message": "Invalid username or password"
                }
            )
        
        # Validate tenant if specified
        if login_data.tenant_id and user.tenant_id != login_data.tenant_id:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "tenant_mismatch",
                    "message": "User does not belong to specified tenant"
                }
            )
        
        # Reset failed login attempts and update last login
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login = datetime.utcnow()
        
        # Generate tokens using OAuth service
        access_token = oauth_service._create_access_token(
            user_id=user.id,
            client_id="internal_client",
            scope="openid profile email",
            tenant_id=user.tenant_id
        )
        
        refresh_token = oauth_service._create_refresh_token(
            user_id=user.id,
            client_id="internal_client",
            scope="openid profile email",
            tenant_id=user.tenant_id
        )
        
        # Create auth session
        session_id = str(uuid.uuid4())
        auth_session = AuthSession(
            id=str(uuid.uuid4()),
            session_id=session_id,
            user_id=user.id,
            tenant_id=user.tenant_id,
            access_token_jti=access_token["jti"],
            refresh_token_jti=refresh_token["jti"],
            expires_at=datetime.utcnow() + timedelta(days=30),
            last_activity=datetime.utcnow()
        )
        
        db.add(auth_session)
        await db.commit()
        
        logger.info(f"User logged in: {user.username} ({user.id})")
        
        return {
            "access_token": access_token["token"],
            "refresh_token": refresh_token["token"],
            "token_type": "Bearer",
            "expires_in": 1800,  # 30 minutes
            "user": UserResponse.from_orm(user),
            "session_id": session_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "error": "login_failed",
                "message": "Failed to authenticate user"
            }
        )


@router.post("/logout")
async def logout_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Logout user and revoke session"""
    
    try:
        token = credentials.credentials
        
        # Decode token to get JTI
        from jose import jwt, JWTError
        from app.core.config import settings
        
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm]
            )
        except JWTError:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "invalid_token",
                    "message": "Invalid access token"
                }
            )
        
        jti = payload.get("jti")
        if not jti:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "invalid_token",
                    "message": "Token missing JTI"
                }
            )
        
        # Find and revoke session
        result = await db.execute(
            select(AuthSession).where(AuthSession.access_token_jti == jti)
        )
        session = result.scalar_one_or_none()
        
        if session:
            session.is_revoked = True
            session.revoked_at = datetime.utcnow()
            session.revoked_reason = "logout"
            await db.commit()
            
            logger.info(f"User logged out, session revoked: {session.session_id}")
        
        return {"message": "Successfully logged out"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during logout: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "logout_failed",
                "message": "Failed to logout user"
            }
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Get current authenticated user information"""
    
    try:
        token = credentials.credentials
        
        # Decode and validate token
        from jose import jwt, JWTError
        from app.core.config import settings
        
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm]
            )
        except JWTError:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "invalid_token",
                    "message": "Invalid access token"
                }
            )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "invalid_token",
                    "message": "Token missing subject"
                }
            )
        
        # Verify session is still active
        jti = payload.get("jti")
        if jti:
            session_result = await db.execute(
                select(AuthSession).where(
                    and_(
                        AuthSession.access_token_jti == jti,
                        AuthSession.is_revoked == False
                    )
                )
            )
            session = session_result.scalar_one_or_none()
            
            if not session:
                raise HTTPException(
                    status_code=401,
                    detail={
                        "error": "session_expired",
                        "message": "Session has been revoked or expired"
                    }
                )
            
            # Update last activity
            session.last_activity = datetime.utcnow()
        
        # Get user
        result = await db.execute(
            select(User).where(
                and_(
                    User.id == user_id,
                    User.is_active == True
                )
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "user_not_found",
                    "message": "User not found or inactive"
                }
            )
        
        await db.commit()
        
        return UserResponse.from_orm(user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting current user: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "user_info_failed",
                "message": "Failed to retrieve user information"
            }
        )


@router.post("/refresh")
async def refresh_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token"""
    
    try:
        # Use OAuth service to refresh token
        token_response = await oauth_service.refresh_access_token(
            db=db,
            refresh_token=refresh_token,
            client_id="internal_client"
        )
        
        if not token_response:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "invalid_refresh_token",
                    "message": "Invalid or expired refresh token"
                }
            )
        
        return token_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing token: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "token_refresh_failed",
                "message": "Failed to refresh token"
            }
        )