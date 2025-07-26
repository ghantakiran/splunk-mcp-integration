"""
Unified Authentication Bridge Service
Coordinates authentication between Splunk Enterprise and Cloud instances
"""

import aiohttp
import asyncio
import json
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
import hashlib
import redis.asyncio as redis
from urllib.parse import urljoin

from app.core.config import settings
from app.core.logging import get_logger
from app.models.auth import (
    AuthRequest,
    AuthResponse,
    UserProfile,
    AuthProvider,
    AuthResult,
    AuthMode
)

logger = get_logger(__name__)


class AuthBridgeService:
    """Unified authentication bridge for hybrid Splunk deployments"""
    
    def __init__(self):
        self.redis_client = None
        self.session_timeout = aiohttp.ClientTimeout(total=30)
        self.auth_providers = {}
        self.auth_cache = {}
        
    async def initialize(self):
        """Initialize the authentication bridge service"""
        try:
            # Initialize Redis connection
            self.redis_client = redis.from_url(
                settings.redis_url,
                password=settings.redis_password,
                db=settings.redis_db,
                max_connections=settings.redis_pool_size,
                decode_responses=True
            )
            
            # Test Redis connection
            await self.redis_client.ping()
            logger.info("Redis connection established successfully")
            
            # Initialize authentication providers
            await self._initialize_auth_providers()
            
            logger.info("Authentication bridge service initialized", 
                       providers=list(self.auth_providers.keys()),
                       mode=settings.auth_bridge_mode)
            
        except Exception as e:
            logger.error("Failed to initialize authentication bridge service", error=str(e))
            raise
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.redis_client:
            await self.redis_client.close()
        
        # Close any open HTTP sessions
        for provider in self.auth_providers.values():
            if hasattr(provider, 'session') and provider.session:
                await provider.session.close()
    
    async def _initialize_auth_providers(self):
        """Initialize authentication providers based on configuration"""
        self.auth_providers = {}
        
        # Initialize Cloud Authentication if available
        if settings.auth_bridge_mode in ["hybrid", "cloud_only"]:
            try:
                cloud_provider = await self._create_cloud_auth_provider()
                if cloud_provider:
                    self.auth_providers["cloud"] = cloud_provider
                    logger.info("Cloud authentication provider initialized")
            except Exception as e:
                logger.warning("Failed to initialize cloud auth provider", error=str(e))
        
        # Initialize Enterprise Authentication if available
        if settings.auth_bridge_mode in ["hybrid", "enterprise_only"]:
            try:
                enterprise_provider = await self._create_enterprise_auth_provider()
                if enterprise_provider:
                    self.auth_providers["enterprise"] = enterprise_provider
                    logger.info("Enterprise authentication provider initialized")
            except Exception as e:
                logger.warning("Failed to initialize enterprise auth provider", error=str(e))
        
        if not self.auth_providers:
            raise Exception("No authentication providers could be initialized")
    
    async def _create_cloud_auth_provider(self) -> Optional[Dict[str, Any]]:
        """Create Splunk Cloud authentication provider"""
        try:
            session = aiohttp.ClientSession(timeout=self.session_timeout)
            
            # Test connection to cloud auth service
            async with session.get(f"{settings.cloud_auth_service_url}/health") as response:
                if response.status == 200:
                    return {
                        "type": "cloud",
                        "name": "Splunk Cloud",
                        "url": settings.cloud_auth_service_url,
                        "session": session,
                        "priority": settings.auth_priority.index("cloud") if "cloud" in settings.auth_priority else 1
                    }
                else:
                    await session.close()
                    return None
        except Exception as e:
            logger.warning("Cloud auth service not available", error=str(e))
            return None
    
    async def _create_enterprise_auth_provider(self) -> Optional[Dict[str, Any]]:
        """Create Splunk Enterprise authentication provider"""
        if not settings.splunk_enterprise_host:
            return None
        
        try:
            session = aiohttp.ClientSession(timeout=self.session_timeout)
            
            # Test connection to Splunk Enterprise
            enterprise_url = f"{settings.splunk_enterprise_scheme}://{settings.splunk_enterprise_host}:{settings.splunk_enterprise_port}"
            async with session.get(f"{enterprise_url}/services/server/info") as response:
                if response.status in [200, 401]:  # 401 is expected without auth
                    return {
                        "type": "enterprise",
                        "name": "Splunk Enterprise",
                        "url": enterprise_url,
                        "session": session,
                        "priority": settings.auth_priority.index("enterprise") if "enterprise" in settings.auth_priority else 2
                    }
                else:
                    await session.close()
                    return None
        except Exception as e:
            logger.warning("Splunk Enterprise not available", error=str(e))
            return None
    
    async def authenticate(self, auth_request: AuthRequest) -> AuthResponse:
        """
        Unified authentication across Splunk Enterprise and Cloud
        
        Args:
            auth_request: Authentication request with credentials
            
        Returns:
            AuthResponse with authentication result and user profile
        """
        try:
            # Check cache first
            cache_key = self._get_auth_cache_key(auth_request.username, auth_request.password)
            cached_result = await self._get_cached_auth_result(cache_key)
            
            if cached_result and settings.auth_cache_ttl > 0:
                logger.info("Authentication result served from cache", 
                           username=auth_request.username)
                return cached_result
            
            # Try authentication providers in priority order
            auth_errors = []
            
            for provider_name in settings.auth_priority:
                if provider_name not in self.auth_providers:
                    continue
                
                provider = self.auth_providers[provider_name]
                
                try:
                    auth_result = await self._authenticate_with_provider(
                        provider, auth_request
                    )
                    
                    if auth_result.success:
                        # Cache successful authentication
                        await self._cache_auth_result(cache_key, auth_result)
                        
                        logger.info("Authentication successful",
                                  username=auth_request.username,
                                  provider=provider_name)
                        
                        return auth_result
                    else:
                        auth_errors.append(f"{provider_name}: {auth_result.error_message}")
                
                except Exception as e:
                    error_msg = f"{provider_name}: {str(e)}"
                    auth_errors.append(error_msg)
                    logger.warning("Authentication provider failed", 
                                 provider=provider_name, error=str(e))
            
            # All providers failed
            error_message = "Authentication failed for all providers"
            if auth_errors:
                error_message += f": {'; '.join(auth_errors)}"
            
            logger.warning("Authentication failed for all providers",
                         username=auth_request.username,
                         errors=auth_errors)
            
            return AuthResponse(
                success=False,
                error_message=error_message,
                provider=AuthProvider.NONE,
                user_profile=None,
                token=None,
                expires_at=None
            )
            
        except Exception as e:
            logger.error("Authentication bridge error", 
                        username=auth_request.username, error=str(e))
            return AuthResponse(
                success=False,
                error_message=f"Authentication service error: {str(e)}",
                provider=AuthProvider.NONE,
                user_profile=None,
                token=None,
                expires_at=None
            )
    
    async def _authenticate_with_provider(
        self, 
        provider: Dict[str, Any], 
        auth_request: AuthRequest
    ) -> AuthResponse:
        """Authenticate with a specific provider"""
        
        if provider["type"] == "cloud":
            return await self._authenticate_cloud(provider, auth_request)
        elif provider["type"] == "enterprise":
            return await self._authenticate_enterprise(provider, auth_request)
        else:
            raise ValueError(f"Unknown provider type: {provider['type']}")
    
    async def _authenticate_cloud(
        self, 
        provider: Dict[str, Any], 
        auth_request: AuthRequest
    ) -> AuthResponse:
        """Authenticate with Splunk Cloud via Cloud Auth Service"""
        
        try:
            auth_data = {
                "username": auth_request.username,
                "password": auth_request.password,
                "tenant_id": auth_request.tenant_id,
                "auth_mode": "bridge"
            }
            
            async with provider["session"].post(
                f"{provider['url']}/api/v1/auth/authenticate",
                json=auth_data
            ) as response:
                result = await response.json()
                
                if response.status == 200 and result.get("success"):
                    data = result.get("data", {})
                    
                    # Extract user profile
                    user_profile = UserProfile(
                        user_id=data.get("user_id"),
                        username=data.get("username"),
                        email=data.get("email"),
                        full_name=data.get("full_name"),
                        roles=data.get("roles", []),
                        permissions=data.get("permissions", {}),
                        tenant_id=data.get("tenant_id"),
                        provider=AuthProvider.CLOUD,
                        accessible_indexes=data.get("accessible_indexes", [])
                    )
                    
                    return AuthResponse(
                        success=True,
                        provider=AuthProvider.CLOUD,
                        user_profile=user_profile,
                        token=data.get("access_token"),
                        refresh_token=data.get("refresh_token"),
                        expires_at=datetime.fromisoformat(data.get("expires_at")) if data.get("expires_at") else None,
                        error_message=None
                    )
                else:
                    return AuthResponse(
                        success=False,
                        provider=AuthProvider.CLOUD,
                        error_message=result.get("error", "Cloud authentication failed"),
                        user_profile=None,
                        token=None,
                        expires_at=None
                    )
        
        except Exception as e:
            logger.error("Cloud authentication error", error=str(e))
            return AuthResponse(
                success=False,
                provider=AuthProvider.CLOUD,
                error_message=f"Cloud auth service error: {str(e)}",
                user_profile=None,
                token=None,
                expires_at=None
            )
    
    async def _authenticate_enterprise(
        self, 
        provider: Dict[str, Any], 
        auth_request: AuthRequest
    ) -> AuthResponse:
        """Authenticate with Splunk Enterprise"""
        
        try:
            # Splunk Enterprise authentication via REST API
            auth_url = f"{provider['url']}/services/auth/login"
            
            auth_data = {
                "username": auth_request.username,
                "password": auth_request.password,
                "output_mode": "json"
            }
            
            async with provider["session"].post(
                auth_url,
                data=auth_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    session_key = result.get("sessionKey")
                    
                    if session_key:
                        # Get user info
                        user_info = await self._get_enterprise_user_info(
                            provider, auth_request.username, session_key
                        )
                        
                        user_profile = UserProfile(
                            user_id=auth_request.username,
                            username=auth_request.username,
                            email=user_info.get("email"),
                            full_name=user_info.get("full_name", auth_request.username),
                            roles=user_info.get("roles", []),
                            permissions=user_info.get("permissions", {}),
                            tenant_id=None,  # Enterprise doesn't have tenants
                            provider=AuthProvider.ENTERPRISE,
                            accessible_indexes=user_info.get("accessible_indexes", ["*"])
                        )
                        
                        return AuthResponse(
                            success=True,
                            provider=AuthProvider.ENTERPRISE,
                            user_profile=user_profile,
                            token=session_key,
                            refresh_token=None,  # Enterprise uses session keys
                            expires_at=datetime.utcnow() + timedelta(hours=24),  # Default 24h
                            error_message=None
                        )
                
                return AuthResponse(
                    success=False,
                    provider=AuthProvider.ENTERPRISE,
                    error_message="Invalid credentials",
                    user_profile=None,
                    token=None,
                    expires_at=None
                )
        
        except Exception as e:
            logger.error("Enterprise authentication error", error=str(e))
            return AuthResponse(
                success=False,
                provider=AuthProvider.ENTERPRISE,
                error_message=f"Enterprise auth error: {str(e)}",
                user_profile=None,
                token=None,
                expires_at=None
            )
    
    async def _get_enterprise_user_info(
        self, 
        provider: Dict[str, Any], 
        username: str, 
        session_key: str
    ) -> Dict[str, Any]:
        """Get user information from Splunk Enterprise"""
        
        try:
            user_url = f"{provider['url']}/services/authentication/users/{username}"
            
            headers = {
                "Authorization": f"Splunk {session_key}",
                "Content-Type": "application/json"
            }
            
            async with provider["session"].get(
                user_url,
                headers=headers,
                params={"output_mode": "json"}
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    entry = result.get("entry", [{}])[0]
                    content = entry.get("content", {})
                    
                    return {
                        "email": content.get("email"),
                        "full_name": content.get("realname", username),
                        "roles": content.get("roles", []),
                        "permissions": {},  # Would need to fetch role capabilities
                        "accessible_indexes": ["*"]  # Default to all indexes
                    }
        
        except Exception as e:
            logger.warning("Failed to get enterprise user info", 
                         username=username, error=str(e))
        
        return {
            "email": None,
            "full_name": username,
            "roles": ["user"],
            "permissions": {},
            "accessible_indexes": ["*"]
        }
    
    async def validate_token(self, token: str, provider: AuthProvider = None) -> Optional[UserProfile]:
        """Validate an authentication token"""
        
        try:
            if provider == AuthProvider.CLOUD or not provider:
                # Try cloud validation first
                cloud_result = await self._validate_cloud_token(token)
                if cloud_result:
                    return cloud_result
            
            if provider == AuthProvider.ENTERPRISE or not provider:
                # Try enterprise validation
                enterprise_result = await self._validate_enterprise_token(token)
                if enterprise_result:
                    return enterprise_result
            
            return None
        
        except Exception as e:
            logger.error("Token validation error", token=token[:10] + "...", error=str(e))
            return None
    
    async def _validate_cloud_token(self, token: str) -> Optional[UserProfile]:
        """Validate cloud authentication token"""
        
        if "cloud" not in self.auth_providers:
            return None
        
        try:
            provider = self.auth_providers["cloud"]
            
            headers = {"Authorization": f"Bearer {token}"}
            
            async with provider["session"].get(
                f"{provider['url']}/api/v1/auth/validate",
                headers=headers
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    if result.get("success"):
                        data = result.get("data", {})
                        
                        return UserProfile(
                            user_id=data.get("user_id"),
                            username=data.get("username"),
                            email=data.get("email"),
                            full_name=data.get("full_name"),
                            roles=data.get("roles", []),
                            permissions=data.get("permissions", {}),
                            tenant_id=data.get("tenant_id"),
                            provider=AuthProvider.CLOUD,
                            accessible_indexes=data.get("accessible_indexes", [])
                        )
        
        except Exception as e:
            logger.warning("Cloud token validation failed", error=str(e))
        
        return None
    
    async def _validate_enterprise_token(self, token: str) -> Optional[UserProfile]:
        """Validate enterprise session key"""
        
        if "enterprise" not in self.auth_providers:
            return None
        
        try:
            provider = self.auth_providers["enterprise"]
            
            headers = {"Authorization": f"Splunk {token}"}
            
            async with provider["session"].get(
                f"{provider['url']}/services/server/info",
                headers=headers,
                params={"output_mode": "json"}
            ) as response:
                
                if response.status == 200:
                    # Token is valid, get user info
                    # For now, return minimal profile
                    return UserProfile(
                        user_id="enterprise_user",
                        username="enterprise_user",
                        email=None,
                        full_name="Enterprise User",
                        roles=["user"],
                        permissions={},
                        tenant_id=None,
                        provider=AuthProvider.ENTERPRISE,
                        accessible_indexes=["*"]
                    )
        
        except Exception as e:
            logger.warning("Enterprise token validation failed", error=str(e))
        
        return None
    
    async def logout(self, token: str, provider: AuthProvider = None) -> bool:
        """Logout from authentication provider"""
        
        try:
            success = False
            
            if provider == AuthProvider.CLOUD or not provider:
                cloud_success = await self._logout_cloud(token)
                success = success or cloud_success
            
            if provider == AuthProvider.ENTERPRISE or not provider:
                enterprise_success = await self._logout_enterprise(token)
                success = success or enterprise_success
            
            # Clear from cache
            await self._clear_auth_cache(token)
            
            return success
        
        except Exception as e:
            logger.error("Logout error", token=token[:10] + "...", error=str(e))
            return False
    
    async def _logout_cloud(self, token: str) -> bool:
        """Logout from cloud provider"""
        
        if "cloud" not in self.auth_providers:
            return False
        
        try:
            provider = self.auth_providers["cloud"]
            headers = {"Authorization": f"Bearer {token}"}
            
            async with provider["session"].post(
                f"{provider['url']}/api/v1/auth/logout",
                headers=headers
            ) as response:
                return response.status == 200
        
        except Exception as e:
            logger.warning("Cloud logout failed", error=str(e))
            return False
    
    async def _logout_enterprise(self, token: str) -> bool:
        """Logout from enterprise provider"""
        
        if "enterprise" not in self.auth_providers:
            return False
        
        try:
            provider = self.auth_providers["enterprise"]
            headers = {"Authorization": f"Splunk {token}"}
            
            # Enterprise logout via DELETE to auth/login
            async with provider["session"].delete(
                f"{provider['url']}/services/auth/login",
                headers=headers
            ) as response:
                return response.status in [200, 204]
        
        except Exception as e:
            logger.warning("Enterprise logout failed", error=str(e))
            return False
    
    def _get_auth_cache_key(self, username: str, password: str) -> str:
        """Generate cache key for authentication result"""
        key_data = f"{username}:{password}:{settings.auth_bridge_mode}"
        return f"auth_bridge:{hashlib.sha256(key_data.encode()).hexdigest()}"
    
    async def _get_cached_auth_result(self, cache_key: str) -> Optional[AuthResponse]:
        """Get cached authentication result"""
        
        try:
            cached_data = await self.redis_client.get(cache_key)
            if cached_data:
                data = json.loads(cached_data)
                
                # Check expiration
                if data.get("expires_at"):
                    expires_at = datetime.fromisoformat(data["expires_at"])
                    if expires_at <= datetime.utcnow():
                        await self.redis_client.delete(cache_key)
                        return None
                
                # Reconstruct AuthResponse
                user_profile = None
                if data.get("user_profile"):
                    user_profile = UserProfile(**data["user_profile"])
                
                return AuthResponse(
                    success=data["success"],
                    provider=AuthProvider(data["provider"]),
                    user_profile=user_profile,
                    token=data.get("token"),
                    refresh_token=data.get("refresh_token"),
                    expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
                    error_message=data.get("error_message")
                )
        
        except Exception as e:
            logger.warning("Failed to get cached auth result", error=str(e))
        
        return None
    
    async def _cache_auth_result(self, cache_key: str, auth_response: AuthResponse):
        """Cache authentication result"""
        
        if settings.auth_cache_ttl <= 0:
            return
        
        try:
            data = {
                "success": auth_response.success,
                "provider": auth_response.provider.value if auth_response.provider else None,
                "token": auth_response.token,
                "refresh_token": auth_response.refresh_token,
                "expires_at": auth_response.expires_at.isoformat() if auth_response.expires_at else None,
                "error_message": auth_response.error_message,
                "user_profile": auth_response.user_profile.dict() if auth_response.user_profile else None
            }
            
            await self.redis_client.setex(
                cache_key,
                settings.auth_cache_ttl,
                json.dumps(data, default=str)
            )
        
        except Exception as e:
            logger.warning("Failed to cache auth result", error=str(e))
    
    async def _clear_auth_cache(self, token: str):
        """Clear authentication cache for a token"""
        
        try:
            # This is a simple implementation - in production you might want
            # to maintain a reverse mapping from token to cache keys
            keys = await self.redis_client.keys("auth_bridge:*")
            for key in keys:
                cached_data = await self.redis_client.get(key)
                if cached_data:
                    data = json.loads(cached_data)
                    if data.get("token") == token:
                        await self.redis_client.delete(key)
        
        except Exception as e:
            logger.warning("Failed to clear auth cache", error=str(e))
    
    async def check_health(self) -> Dict[str, str]:
        """Check health of dependent services"""
        
        services = {}
        
        # Check cloud auth service
        if "cloud" in self.auth_providers:
            try:
                provider = self.auth_providers["cloud"]
                async with provider["session"].get(
                    f"{provider['url']}/health",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    services["cloud_auth_service"] = "healthy" if response.status == 200 else "unhealthy"
            except:
                services["cloud_auth_service"] = "unhealthy"
        else:
            services["cloud_auth_service"] = "disabled"
        
        # Check enterprise Splunk
        if "enterprise" in self.auth_providers:
            try:
                provider = self.auth_providers["enterprise"]
                async with provider["session"].get(
                    f"{provider['url']}/services/server/info",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    services["splunk_enterprise"] = "healthy" if response.status in [200, 401] else "unhealthy"
            except:
                services["splunk_enterprise"] = "unhealthy"
        else:
            services["splunk_enterprise"] = "disabled"
        
        # Check API Gateway
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(f"{settings.api_gateway_url}/health") as response:
                    services["api_gateway"] = "healthy" if response.status == 200 else "unhealthy"
        except:
            services["api_gateway"] = "unhealthy"
        
        # Check Cloud Connection Manager
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(f"{settings.cloud_connection_manager_url}/health") as response:
                    services["cloud_connection_manager"] = "healthy" if response.status == 200 else "unhealthy"
        except:
            services["cloud_connection_manager"] = "unhealthy"
        
        return services
    
    async def get_provider_status(self) -> Dict[str, Any]:
        """Get status of authentication providers"""
        
        provider_status = {}
        
        for name, provider in self.auth_providers.items():
            provider_status[name] = {
                "type": provider["type"],
                "name": provider["name"],
                "url": provider["url"],
                "priority": provider["priority"],
                "status": "active"
            }
        
        return {
            "mode": settings.auth_bridge_mode,
            "priority_order": settings.auth_priority,
            "fallback_enabled": settings.auth_fallback_enabled,
            "cache_ttl": settings.auth_cache_ttl,
            "providers": provider_status
        }