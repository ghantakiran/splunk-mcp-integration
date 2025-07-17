"""
Microsoft Teams authentication and verification utilities.
"""

import hashlib
import hmac
import json
import jwt
import time
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException, Depends
import aiohttp
from cryptography.x509 import load_pem_x509_certificate
from cryptography.hazmat.primitives import hashes

from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)

class TeamsAuthenticator:
    """Teams authentication and verification utilities."""
    
    def __init__(self):
        self.microsoft_app_id = settings.microsoft_app_id
        self.microsoft_app_password = settings.microsoft_app_password
        self.bot_framework_url = settings.bot_framework_url
        self._openid_metadata = None
        self._signing_keys = {}
    
    async def initialize(self):
        """Initialize authenticator with OpenID metadata."""
        try:
            await self._load_openid_metadata()
            logger.info("Teams authenticator initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Teams authenticator: {str(e)}")
            raise
    
    async def _load_openid_metadata(self):
        """Load OpenID metadata from Microsoft."""
        metadata_url = "https://login.botframework.com/v1/.well-known/openidconfiguration"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(metadata_url) as response:
                    if response.status == 200:
                        self._openid_metadata = await response.json()
                        await self._load_signing_keys()
                    else:
                        raise Exception(f"Failed to load OpenID metadata: {response.status}")
        except Exception as e:
            logger.error(f"Error loading OpenID metadata: {str(e)}")
            raise
    
    async def _load_signing_keys(self):
        """Load JWT signing keys from Microsoft."""
        if not self._openid_metadata:
            return
        
        jwks_uri = self._openid_metadata.get("jwks_uri")
        if not jwks_uri:
            return
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(jwks_uri) as response:
                    if response.status == 200:
                        jwks = await response.json()
                        for key in jwks.get("keys", []):
                            kid = key.get("kid")
                            if kid:
                                self._signing_keys[kid] = key
        except Exception as e:
            logger.error(f"Error loading signing keys: {str(e)}")
    
    async def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token from Teams."""
        try:
            # Decode header to get key ID
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            
            if not kid or kid not in self._signing_keys:
                logger.warning("JWT key ID not found in signing keys")
                return None
            
            # Get signing key
            signing_key = self._signing_keys[kid]
            
            # Verify token
            payload = jwt.decode(
                token,
                key=signing_key,
                algorithms=["RS256"],
                audience=self.microsoft_app_id,
                issuer="https://api.botframework.com"
            )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error verifying JWT token: {str(e)}")
            return None
    
    def verify_teams_signature(self, body: bytes, signature: str) -> bool:
        """Verify Teams request signature."""
        try:
            # Teams uses HMAC-SHA256 with app password
            expected_signature = hmac.new(
                self.microsoft_app_password.encode(),
                body,
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception as e:
            logger.error(f"Error verifying Teams signature: {str(e)}")
            return False
    
    async def authenticate_service_to_service(self) -> Optional[str]:
        """Get service-to-service authentication token."""
        try:
            token_url = "https://login.microsoftonline.com/botframework.com/oauth2/v2.0/token"
            
            data = {
                "grant_type": "client_credentials",
                "client_id": self.microsoft_app_id,
                "client_secret": self.microsoft_app_password,
                "scope": "https://api.botframework.com/.default"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(token_url, data=data) as response:
                    if response.status == 200:
                        token_response = await response.json()
                        return token_response.get("access_token")
                    else:
                        logger.error(f"Failed to get service token: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error getting service token: {str(e)}")
            return None

# Global authenticator instance
authenticator = TeamsAuthenticator()

async def verify_teams_request(request: Request) -> Dict[str, Any]:
    """Verify and parse Teams request."""
    try:
        # Get authorization header
        auth_header = request.headers.get("authorization", "")
        
        if not auth_header.startswith("Bearer "):
            logger.warning("Missing or invalid authorization header")
            raise HTTPException(status_code=401, detail="Missing authorization header")
        
        # Extract token
        token = auth_header[7:]  # Remove "Bearer " prefix
        
        # Verify JWT token
        payload = await authenticator.verify_jwt_token(token)
        if not payload:
            logger.warning("Invalid JWT token")
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Get request body
        body = await request.body()
        
        # Parse JSON body
        try:
            activity = json.loads(body.decode('utf-8'))
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON")
        
        # Additional validation
        if not activity.get("type"):
            raise HTTPException(status_code=400, detail="Missing activity type")
        
        # Verify channel ID matches token
        service_url = activity.get("serviceUrl", "")
        token_service_url = payload.get("serviceurl", "")
        
        if service_url and token_service_url and service_url != token_service_url:
            logger.warning("Service URL mismatch")
            raise HTTPException(status_code=401, detail="Service URL mismatch")
        
        return activity
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying Teams request: {str(e)}")
        raise HTTPException(status_code=500, detail="Request verification failed")

def verify_webhook_signature(request: Request, body: bytes) -> bool:
    """Verify webhook signature for Teams."""
    signature = request.headers.get("X-Hub-Signature-256", "")
    
    if not signature:
        return False
    
    return authenticator.verify_teams_signature(body, signature.replace("sha256=", ""))

class TeamsAuth:
    """Teams authentication utilities."""
    
    @staticmethod
    async def get_user_token(user_id: str) -> Optional[str]:
        """Get user-specific token (for OAuth scenarios)."""
        # This would integrate with OAuth token storage
        # For now, return None as we're using app-only authentication
        return None
    
    @staticmethod
    def verify_user_permissions(user_id: str, required_permissions: list = None) -> bool:
        """Verify user has required permissions."""
        # This would integrate with user permission system
        # For now, allow all authenticated users
        return True
    
    @staticmethod
    def is_admin_user(user_id: str) -> bool:
        """Check if user is an admin."""
        # This would check against admin user list
        # For now, return False (no special admin privileges)
        return False
    
    @staticmethod
    def extract_user_info(activity: Dict[str, Any]) -> Dict[str, Any]:
        """Extract user information from Teams activity."""
        from_user = activity.get("from", {})
        
        return {
            "id": from_user.get("id", ""),
            "name": from_user.get("name", ""),
            "aad_object_id": from_user.get("aadObjectId", ""),
            "tenant_id": activity.get("conversation", {}).get("tenantId", ""),
            "conversation_type": activity.get("conversation", {}).get("conversationType", ""),
            "channel_id": activity.get("channelId", "")
        }
    
    @staticmethod
    def extract_conversation_info(activity: Dict[str, Any]) -> Dict[str, Any]:
        """Extract conversation information from Teams activity."""
        conversation = activity.get("conversation", {})
        
        return {
            "id": conversation.get("id", ""),
            "conversation_type": conversation.get("conversationType", ""),
            "tenant_id": conversation.get("tenantId", ""),
            "is_group": conversation.get("isGroup", False),
            "name": conversation.get("name", "")
        }