"""
Authentication service with business logic
"""

import json
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
import redis.asyncio as redis
from fastapi import HTTPException, status, Request

from ..core.config import settings
from ..core.security import security_manager
from ..core.logging import get_logger
from ..core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ValidationError,
    ServiceError
)
from ..models.user import User
from ..models.auth import (
    UserLogin,
    UserRegister,
    TokenResponse,
    LoginResponse,
    UserProfile,
    SessionInfo,
    PasswordStrengthResponse
)

logger = get_logger(__name__)


class AuthService:
    """Authentication service for handling user authentication and authorization"""
    
    def __init__(self):
        self.security_manager = security_manager
    
    async def authenticate_user(
        self,
        db: AsyncSession,
        email: str,
        password: str
    ) -> Optional[User]:
        """Authenticate user by email and password"""
        try:
            # Get user by email
            result = await db.execute(
                select(User).where(User.email == email.lower())
            )
            user = result.scalar_one_or_none()
            
            if not user:
                logger.warning("Authentication failed: user not found", email=email)
                return None
            
            if not user.is_active:
                logger.warning("Authentication failed: user inactive", email=email, user_id=str(user.id))
                return None
            
            # Verify password
            if not self.security_manager.verify_password(password, user.password_hash):
                logger.warning("Authentication failed: invalid password", email=email, user_id=str(user.id))
                return None
            
            logger.info("User authenticated successfully", email=email, user_id=str(user.id))
            return user
            
        except Exception as e:
            logger.error("Authentication error", error=str(e), email=email, exc_info=True)
            return None
    
    async def create_user_tokens(
        self,
        user: User,
        remember_me: bool = False
    ) -> TokenResponse:
        """Create access and refresh tokens for user"""
        try:
            # Token data
            token_data = {
                "sub": str(user.id),
                "username": user.username,
                "email": user.email,
                "roles": user.roles,
                "permissions": user.permissions,
                "is_verified": user.is_verified
            }
            
            # Create tokens
            access_token_expires = timedelta(minutes=settings.jwt_expire_minutes)
            refresh_token_expires = timedelta(
                days=settings.jwt_refresh_expire_days_extended if remember_me 
                else settings.jwt_refresh_expire_days
            )
            
            access_token = self.security_manager.create_access_token(
                token_data, access_token_expires
            )
            refresh_token = self.security_manager.create_refresh_token(
                token_data, refresh_token_expires
            )
            
            return TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=settings.jwt_expire_minutes * 60,
                user_id=user.id,
                username=user.username,
                roles=user.roles
            )
            
        except Exception as e:
            logger.error("Token creation error", error=str(e), user_id=str(user.id), exc_info=True)
            raise ServiceError("Failed to create authentication tokens")
    
    async def create_user_session(
        self,
        redis_client: redis.Redis,
        user: User,
        request: Request,
        tokens: TokenResponse
    ) -> SessionInfo:
        """Create user session in Redis"""
        try:
            session_id = self.security_manager.generate_session_token()
            session_key = f"session:{user.id}"
            
            # Session data
            session_data = {
                "session_id": session_id,
                "user_id": str(user.id),
                "username": user.username,
                "email": user.email,
                "roles": user.roles,
                "created_at": datetime.utcnow().isoformat(),
                "last_activity": datetime.utcnow().isoformat(),
                "ip_address": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
                "access_token": tokens.access_token,
                "refresh_token": tokens.refresh_token
            }
            
            # Store session in Redis
            session_timeout = settings.session_timeout_minutes * 60
            await redis_client.setex(
                session_key,
                session_timeout,
                json.dumps(session_data)
            )
            
            # Create session info response
            expires_at = datetime.utcnow() + timedelta(minutes=settings.session_timeout_minutes)
            
            return SessionInfo(
                session_id=session_id,
                user_id=user.id,
                created_at=datetime.utcnow(),
                last_activity=datetime.utcnow(),
                ip_address=session_data["ip_address"],
                user_agent=session_data["user_agent"],
                expires_at=expires_at
            )
            
        except Exception as e:
            logger.error("Session creation error", error=str(e), user_id=str(user.id), exc_info=True)
            raise ServiceError("Failed to create user session")
    
    async def login_user(
        self,
        db: AsyncSession,
        redis_client: redis.Redis,
        request: Request,
        login_data: UserLogin
    ) -> LoginResponse:
        """Complete user login process"""
        try:
            # Authenticate user
            user = await self.authenticate_user(db, login_data.email, login_data.password)
            if not user:
                raise AuthenticationError("Invalid email or password")
            
            # Create tokens
            tokens = await self.create_user_tokens(user, login_data.remember_me)
            
            # Create session
            session = await self.create_user_session(redis_client, user, request, tokens)
            
            # Update user login info
            await db.execute(
                update(User)
                .where(User.id == user.id)
                .values(
                    last_login=datetime.utcnow(),
                    login_count=User.login_count + 1
                )
            )
            await db.commit()
            
            # Create user profile
            user_profile = UserProfile.from_orm(user)
            
            # Log successful login
            logger.info(
                "User login successful",
                user_id=str(user.id),
                username=user.username,
                ip_address=session.ip_address
            )
            
            return LoginResponse(
                tokens=tokens,
                user=user_profile,
                session=session,
                message="Login successful"
            )
            
        except AuthenticationError:
            raise
        except Exception as e:
            logger.error("Login error", error=str(e), exc_info=True)
            raise ServiceError("Login failed")
    
    async def logout_user(
        self,
        redis_client: redis.Redis,
        user: User
    ) -> Dict[str, Any]:
        """Logout user and revoke session"""
        try:
            session_key = f"session:{user.id}"
            
            # Get session data before deletion
            session_data = await redis_client.get(session_key)
            
            # Delete session from Redis
            deleted_count = await redis_client.delete(session_key)
            
            # Log logout
            logger.info(
                "User logout successful",
                user_id=str(user.id),
                username=user.username,
                revoked_sessions=deleted_count
            )
            
            return {
                "message": "Logout successful",
                "revoked_tokens": deleted_count
            }
            
        except Exception as e:
            logger.error("Logout error", error=str(e), user_id=str(user.id), exc_info=True)
            raise ServiceError("Logout failed")
    
    async def refresh_tokens(
        self,
        db: AsyncSession,
        redis_client: redis.Redis,
        refresh_token: str
    ) -> TokenResponse:
        """Refresh access token using refresh token"""
        try:
            # Verify refresh token
            payload = self.security_manager.verify_token(refresh_token)
            if not payload or payload.get("type") != "refresh":
                raise AuthenticationError("Invalid refresh token")
            
            user_id = payload.get("sub")
            if not user_id:
                raise AuthenticationError("Invalid token payload")
            
            # Get user from database
            result = await db.execute(
                select(User).where(User.id == UUID(user_id))
            )
            user = result.scalar_one_or_none()
            
            if not user or not user.is_active:
                raise AuthenticationError("User not found or inactive")
            
            # Verify session exists
            session_key = f"session:{user.id}"
            session_data = await redis_client.get(session_key)
            
            if not session_data:
                raise AuthenticationError("Session expired")
            
            # Create new tokens
            tokens = await self.create_user_tokens(user)
            
            # Update session with new tokens
            session_info = json.loads(session_data)
            session_info["access_token"] = tokens.access_token
            session_info["refresh_token"] = tokens.refresh_token
            session_info["last_activity"] = datetime.utcnow().isoformat()
            
            await redis_client.setex(
                session_key,
                settings.session_timeout_minutes * 60,
                json.dumps(session_info)
            )
            
            logger.info(
                "Tokens refreshed successfully",
                user_id=str(user.id),
                username=user.username
            )
            
            return tokens
            
        except AuthenticationError:
            raise
        except Exception as e:
            logger.error("Token refresh error", error=str(e), exc_info=True)
            raise ServiceError("Token refresh failed")
    
    async def register_user(
        self,
        db: AsyncSession,
        registration_data: UserRegister
    ) -> User:
        """Register new user"""
        try:
            # Check if user already exists
            result = await db.execute(
                select(User).where(
                    (User.email == registration_data.email.lower()) |
                    (User.username == registration_data.username.lower())
                )
            )
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                if existing_user.email == registration_data.email.lower():
                    raise ValidationError("Email address already registered")
                else:
                    raise ValidationError("Username already taken")
            
            # Validate password strength
            password_validation = self.security_manager.validate_password_strength(
                registration_data.password
            )
            
            if not password_validation["is_valid"]:
                raise ValidationError(f"Password validation failed: {', '.join(password_validation['errors'])}")
            
            # Hash password
            password_hash = self.security_manager.get_password_hash(registration_data.password)
            
            # Create new user
            new_user = User(
                username=registration_data.username.lower(),
                email=registration_data.email.lower(),
                password_hash=password_hash,
                first_name=registration_data.first_name,
                last_name=registration_data.last_name,
                is_active=True,
                is_verified=False,  # Email verification required
                roles=["user"],  # Default role
                permissions={},
                preferences={}
            )
            
            db.add(new_user)
            await db.commit()
            await db.refresh(new_user)
            
            logger.info(
                "User registered successfully",
                user_id=str(new_user.id),
                username=new_user.username,
                email=new_user.email
            )
            
            return new_user
            
        except (ValidationError, AuthenticationError):
            raise
        except Exception as e:
            logger.error("User registration error", error=str(e), exc_info=True)
            await db.rollback()
            raise ServiceError("User registration failed")
    
    async def validate_password_strength(self, password: str) -> PasswordStrengthResponse:
        """Validate password strength"""
        try:
            validation = self.security_manager.validate_password_strength(password)
            
            # Add suggestions for improvement
            suggestions = []
            if validation["score"] < 3:
                suggestions.append("Consider using a longer password")
            if "uppercase" in str(validation.get("errors", [])):
                suggestions.append("Add uppercase letters")
            if "lowercase" in str(validation.get("errors", [])):
                suggestions.append("Add lowercase letters")
            if "digit" in str(validation.get("errors", [])):
                suggestions.append("Add numbers")
            if "special" in str(validation.get("errors", [])):
                suggestions.append("Add special characters (!@#$%^&*)")
            
            return PasswordStrengthResponse(
                is_valid=validation["is_valid"],
                strength=validation["strength"],
                score=validation["score"],
                errors=validation["errors"],
                suggestions=suggestions
            )
            
        except Exception as e:
            logger.error("Password validation error", error=str(e), exc_info=True)
            raise ServiceError("Password validation failed")
    
    async def get_user_sessions(
        self,
        redis_client: redis.Redis,
        user: User
    ) -> Dict[str, Any]:
        """Get user session information"""
        try:
            session_key = f"session:{user.id}"
            session_data = await redis_client.get(session_key)
            
            if not session_data:
                return {"active_sessions": 0, "sessions": []}
            
            session_info = json.loads(session_data)
            
            return {
                "active_sessions": 1,
                "sessions": [session_info]
            }
            
        except Exception as e:
            logger.error("Get sessions error", error=str(e), user_id=str(user.id), exc_info=True)
            return {"active_sessions": 0, "sessions": []}


# Global auth service instance
auth_service = AuthService()