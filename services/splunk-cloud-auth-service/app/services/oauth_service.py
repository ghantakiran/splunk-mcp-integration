"""
OAuth 2.0 service implementation for Splunk Cloud authentication
"""

import secrets
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from urllib.parse import urlencode, parse_qs, urlparse
import aiohttp
import asyncio
import logging
from jose import jwt, JWTError
from passlib.context import CryptContext
import uuid

from app.core.config import settings
from app.models.auth_models import (
    OAuthClient, 
    AuthorizationCode, 
    User, 
    AuthSession,
    TokenResponse,
    TokenIntrospectionResponse
)
from app.core.database import AsyncSession

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class OAuthService:
    """OAuth 2.0 service for Splunk Cloud authentication"""
    
    def __init__(self):
        self.token_url = settings.oauth_token_url
        self.authorization_url = settings.oauth_authorization_url
        self.client_id = settings.oauth_client_id
        self.client_secret = settings.oauth_client_secret
        self.redirect_uri = settings.oauth_redirect_uri
        self.scope = settings.oauth_scope
    
    async def create_client(
        self, 
        db: AsyncSession, 
        client_name: str,
        redirect_uris: List[str],
        allowed_scopes: List[str],
        allowed_grant_types: List[str],
        tenant_id: Optional[str] = None,
        require_pkce: bool = True,
        is_confidential: bool = True
    ) -> OAuthClient:
        """Create a new OAuth 2.0 client"""
        
        # Generate client credentials
        client_id = f"splunk_cloud_{secrets.token_urlsafe(16)}"
        client_secret = secrets.token_urlsafe(32)
        client_secret_hash = pwd_context.hash(client_secret)
        
        client = OAuthClient(
            id=str(uuid.uuid4()),
            client_id=client_id,
            client_secret_hash=client_secret_hash,
            client_name=client_name,
            tenant_id=tenant_id,
            redirect_uris=redirect_uris,
            allowed_scopes=allowed_scopes,
            allowed_grant_types=allowed_grant_types,
            require_pkce=require_pkce,
            is_confidential=is_confidential
        )
        
        db.add(client)
        await db.commit()
        await db.refresh(client)
        
        logger.info(f"Created OAuth client: {client_id} for tenant: {tenant_id}")
        
        # Return client with plaintext secret (only time it's available)
        client.client_secret = client_secret
        return client
    
    async def validate_client(
        self, 
        db: AsyncSession, 
        client_id: str, 
        client_secret: Optional[str] = None
    ) -> Optional[OAuthClient]:
        """Validate OAuth client credentials"""
        
        from sqlalchemy import select
        
        result = await db.execute(
            select(OAuthClient).where(
                OAuthClient.client_id == client_id,
                OAuthClient.is_active == True
            )
        )
        client = result.scalar_one_or_none()
        
        if not client:
            logger.warning(f"Client not found: {client_id}")
            return None
        
        # For confidential clients, verify secret
        if client.is_confidential and client_secret:
            if not pwd_context.verify(client_secret, client.client_secret_hash):
                logger.warning(f"Invalid client secret for: {client_id}")
                return None
        
        return client
    
    def generate_authorization_url(
        self,
        client_id: str,
        redirect_uri: str,
        scope: str = "openid profile email",
        state: Optional[str] = None,
        code_challenge: Optional[str] = None,
        code_challenge_method: str = "S256"
    ) -> str:
        """Generate OAuth 2.0 authorization URL"""
        
        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope
        }
        
        if state:
            params["state"] = state
        
        # PKCE support
        if code_challenge:
            params["code_challenge"] = code_challenge
            params["code_challenge_method"] = code_challenge_method
        
        url = f"{self.authorization_url}?{urlencode(params)}"
        logger.info(f"Generated authorization URL for client: {client_id}")
        return url
    
    async def create_authorization_code(
        self,
        db: AsyncSession,
        client_id: str,
        user_id: str,
        redirect_uri: str,
        scope: str,
        state: Optional[str] = None,
        code_challenge: Optional[str] = None,
        code_challenge_method: Optional[str] = None
    ) -> str:
        """Create authorization code for OAuth flow"""
        
        # Generate authorization code
        code = secrets.token_urlsafe(32)
        
        # Calculate expiration (10 minutes)
        expires_at = datetime.utcnow() + timedelta(minutes=10)
        
        auth_code = AuthorizationCode(
            id=str(uuid.uuid4()),
            code=code,
            client_id=client_id,
            user_id=user_id,
            redirect_uri=redirect_uri,
            scope=scope,
            state=state,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            expires_at=expires_at
        )
        
        db.add(auth_code)
        await db.commit()
        
        logger.info(f"Created authorization code for user: {user_id}, client: {client_id}")
        return code
    
    async def exchange_code_for_tokens(
        self,
        db: AsyncSession,
        code: str,
        client_id: str,
        client_secret: Optional[str],
        redirect_uri: str,
        code_verifier: Optional[str] = None
    ) -> Optional[TokenResponse]:
        """Exchange authorization code for access and refresh tokens"""
        
        from sqlalchemy import select, and_
        
        # Find and validate authorization code
        result = await db.execute(
            select(AuthorizationCode).where(
                and_(
                    AuthorizationCode.code == code,
                    AuthorizationCode.client_id == client_id,
                    AuthorizationCode.redirect_uri == redirect_uri,
                    AuthorizationCode.is_used == False,
                    AuthorizationCode.expires_at > datetime.utcnow()
                )
            )
        )
        auth_code = result.scalar_one_or_none()
        
        if not auth_code:
            logger.warning(f"Invalid or expired authorization code: {code}")
            return None
        
        # Validate client
        client = await self.validate_client(db, client_id, client_secret)
        if not client:
            return None
        
        # PKCE validation
        if auth_code.code_challenge and code_verifier:
            if not self._verify_pkce(code_verifier, auth_code.code_challenge, auth_code.code_challenge_method):
                logger.warning("PKCE verification failed")
                return None
        elif client.require_pkce:
            logger.warning("PKCE required but not provided")
            return None
        
        # Mark code as used
        auth_code.is_used = True
        auth_code.used_at = datetime.utcnow()
        
        # Get user information
        user_result = await db.execute(
            select(User).where(User.id == auth_code.user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            logger.error(f"User not found: {auth_code.user_id}")
            return None
        
        # Generate tokens
        access_token = self._create_access_token(
            user_id=user.id,
            client_id=client_id,
            scope=auth_code.scope,
            tenant_id=user.tenant_id
        )
        
        refresh_token = self._create_refresh_token(
            user_id=user.id,
            client_id=client_id,
            scope=auth_code.scope,
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
        
        logger.info(f"Exchanged code for tokens, user: {user.id}, client: {client_id}")
        
        return TokenResponse(
            access_token=access_token["token"],
            token_type="Bearer",
            expires_in=settings.jwt_access_token_expire_minutes * 60,
            refresh_token=refresh_token["token"],
            scope=auth_code.scope
        )
    
    async def refresh_access_token(
        self,
        db: AsyncSession,
        refresh_token: str,
        client_id: str,
        client_secret: Optional[str] = None
    ) -> Optional[TokenResponse]:
        """Refresh access token using refresh token"""
        
        # Validate client
        client = await self.validate_client(db, client_id, client_secret)
        if not client:
            return None
        
        # Decode and validate refresh token
        try:
            payload = jwt.decode(
                refresh_token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm]
            )
        except JWTError as e:
            logger.warning(f"Invalid refresh token: {e}")
            return None
        
        # Validate token type and expiration
        if payload.get("type") != "refresh" or payload.get("exp", 0) < datetime.utcnow().timestamp():
            logger.warning("Invalid or expired refresh token")
            return None
        
        user_id = payload.get("sub")
        tenant_id = payload.get("tenant_id")
        scope = payload.get("scope", "openid profile email")
        
        # Generate new access token
        access_token = self._create_access_token(
            user_id=user_id,
            client_id=client_id,
            scope=scope,
            tenant_id=tenant_id
        )
        
        logger.info(f"Refreshed access token for user: {user_id}, client: {client_id}")
        
        return TokenResponse(
            access_token=access_token["token"],
            token_type="Bearer",
            expires_in=settings.jwt_access_token_expire_minutes * 60,
            scope=scope
        )
    
    async def introspect_token(
        self,
        db: AsyncSession,
        token: str,
        client_id: str,
        client_secret: Optional[str] = None
    ) -> TokenIntrospectionResponse:
        """Introspect access token"""
        
        # Validate client
        client = await self.validate_client(db, client_id, client_secret)
        if not client:
            return TokenIntrospectionResponse(active=False)
        
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm]
            )
        except JWTError:
            return TokenIntrospectionResponse(active=False)
        
        # Check if token is expired
        if payload.get("exp", 0) < datetime.utcnow().timestamp():
            return TokenIntrospectionResponse(active=False)
        
        # Check if session is still active
        from sqlalchemy import select
        
        jti = payload.get("jti")
        if jti:
            result = await db.execute(
                select(AuthSession).where(
                    AuthSession.access_token_jti == jti,
                    AuthSession.is_revoked == False
                )
            )
            session = result.scalar_one_or_none()
            
            if not session:
                return TokenIntrospectionResponse(active=False)
        
        return TokenIntrospectionResponse(
            active=True,
            scope=payload.get("scope"),
            client_id=payload.get("aud"),
            username=payload.get("preferred_username"),
            token_type="Bearer",
            exp=payload.get("exp"),
            iat=payload.get("iat"),
            sub=payload.get("sub"),
            aud=payload.get("aud"),
            iss=payload.get("iss"),
            jti=payload.get("jti")
        )
    
    async def revoke_token(
        self,
        db: AsyncSession,
        token: str,
        client_id: str,
        client_secret: Optional[str] = None
    ) -> bool:
        """Revoke access or refresh token"""
        
        # Validate client
        client = await self.validate_client(db, client_id, client_secret)
        if not client:
            return False
        
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm]
            )
        except JWTError:
            return False
        
        jti = payload.get("jti")
        if not jti:
            return False
        
        # Find and revoke session
        from sqlalchemy import select, or_
        
        result = await db.execute(
            select(AuthSession).where(
                or_(
                    AuthSession.access_token_jti == jti,
                    AuthSession.refresh_token_jti == jti
                )
            )
        )
        session = result.scalar_one_or_none()
        
        if session:
            session.is_revoked = True
            session.revoked_at = datetime.utcnow()
            session.revoked_reason = "token_revoked"
            await db.commit()
            
            logger.info(f"Revoked token session: {session.session_id}")
            return True
        
        return False
    
    def _create_access_token(
        self,
        user_id: str,
        client_id: str,
        scope: str,
        tenant_id: Optional[str] = None
    ) -> Dict[str, str]:
        """Create JWT access token"""
        
        now = datetime.utcnow()
        jti = str(uuid.uuid4())
        
        payload = {
            "iss": "splunk-cloud-auth-service",
            "sub": user_id,
            "aud": client_id,
            "exp": now + timedelta(minutes=settings.jwt_access_token_expire_minutes),
            "iat": now,
            "jti": jti,
            "type": "access",
            "scope": scope
        }
        
        if tenant_id:
            payload["tenant_id"] = tenant_id
        
        token = jwt.encode(
            payload,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm
        )
        
        return {"token": token, "jti": jti}
    
    def _create_refresh_token(
        self,
        user_id: str,
        client_id: str,
        scope: str,
        tenant_id: Optional[str] = None
    ) -> Dict[str, str]:
        """Create JWT refresh token"""
        
        now = datetime.utcnow()
        jti = str(uuid.uuid4())
        
        payload = {
            "iss": "splunk-cloud-auth-service",
            "sub": user_id,
            "aud": client_id,
            "exp": now + timedelta(days=settings.jwt_refresh_token_expire_days),
            "iat": now,
            "jti": jti,
            "type": "refresh",
            "scope": scope
        }
        
        if tenant_id:
            payload["tenant_id"] = tenant_id
        
        token = jwt.encode(
            payload,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm
        )
        
        return {"token": token, "jti": jti}
    
    def _verify_pkce(
        self,
        code_verifier: str,
        code_challenge: str,
        code_challenge_method: str = "S256"
    ) -> bool:
        """Verify PKCE code challenge"""
        
        if code_challenge_method == "S256":
            # SHA256 hash of code_verifier, base64url encoded
            digest = hashlib.sha256(code_verifier.encode()).digest()
            challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
            return challenge == code_challenge
        elif code_challenge_method == "plain":
            return code_verifier == code_challenge
        else:
            return False
    
    async def get_splunk_cloud_token(
        self,
        cloud_instance_url: str,
        client_id: str,
        client_secret: str,
        scope: str = "openid profile email"
    ) -> Optional[Dict[str, Any]]:
        """Get access token from Splunk Cloud directly"""
        
        token_endpoint = f"{cloud_instance_url}/services/auth/oauth2/token"
        
        data = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": scope
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    token_endpoint,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"Successfully obtained Splunk Cloud token for: {cloud_instance_url}")
                        return result
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to get Splunk Cloud token: {response.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"Error getting Splunk Cloud token: {e}")
            return None