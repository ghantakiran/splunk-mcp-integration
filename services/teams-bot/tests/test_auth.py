"""
Tests for Microsoft Teams authentication functionality.
"""

import pytest
import jwt
import time
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
import httpx

from app.bot.auth import (
    verify_teams_signature,
    get_openid_metadata,
    verify_jwt_token,
    TeamsAuthenticationError,
    AuthenticationMiddleware
)


class TestTeamsAuthentication:
    """Test suite for Teams authentication."""
    
    @pytest.mark.asyncio
    async def test_get_openid_metadata_success(self):
        """Test successful OpenID metadata retrieval."""
        mock_metadata = {
            "issuer": "https://login.microsoftonline.com/botframework",
            "jwks_uri": "https://login.microsoftonline.com/botframework/v2.0/.well-known/keys",
            "token_endpoint": "https://login.microsoftonline.com/botframework/oauth2/v2.0/token"
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.json.return_value = mock_metadata
            mock_response.raise_for_status = AsyncMock()
            
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            result = await get_openid_metadata()
            
            assert result == mock_metadata
            assert result["issuer"] == "https://login.microsoftonline.com/botframework"
    
    @pytest.mark.asyncio
    async def test_get_openid_metadata_cached(self):
        """Test OpenID metadata caching."""
        mock_metadata = {"issuer": "test", "jwks_uri": "test"}
        
        # First call
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.json.return_value = mock_metadata
            mock_response.raise_for_status = AsyncMock()
            
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            result1 = await get_openid_metadata()
            result2 = await get_openid_metadata()
            
            # Should only make one HTTP call due to caching
            assert mock_client.return_value.__aenter__.return_value.get.call_count == 1
            assert result1 == result2
    
    @pytest.mark.asyncio
    async def test_get_openid_metadata_failure(self):
        """Test OpenID metadata retrieval failure."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get.side_effect = httpx.RequestError("Network error")
            
            with pytest.raises(TeamsAuthenticationError):
                await get_openid_metadata()
    
    def test_verify_jwt_token_valid(self):
        """Test JWT token verification with valid token."""
        # Create a test JWT token
        payload = {
            "iss": "https://login.microsoftonline.com/botframework",
            "aud": "test-app-id",
            "exp": int(time.time()) + 3600,  # Expires in 1 hour
            "iat": int(time.time()),
            "sub": "test-bot-id"
        }
        
        secret = "test-secret"
        token = jwt.encode(payload, secret, algorithm="HS256")
        
        # Mock key retrieval
        mock_key = {"kty": "RSA", "kid": "test-key", "use": "sig"}
        
        with patch("app.bot.auth.jwt.decode") as mock_decode:
            mock_decode.return_value = payload
            
            result = verify_jwt_token(token, [mock_key], "test-app-id")
            
            assert result == payload
            mock_decode.assert_called_once()
    
    def test_verify_jwt_token_expired(self):
        """Test JWT token verification with expired token."""
        # Create an expired token
        payload = {
            "iss": "https://login.microsoftonline.com/botframework",
            "aud": "test-app-id",
            "exp": int(time.time()) - 3600,  # Expired 1 hour ago
            "iat": int(time.time()) - 7200
        }
        
        secret = "test-secret"
        token = jwt.encode(payload, secret, algorithm="HS256")
        mock_key = {"kty": "RSA", "kid": "test-key"}
        
        with patch("app.bot.auth.jwt.decode") as mock_decode:
            mock_decode.side_effect = jwt.ExpiredSignatureError("Token expired")
            
            with pytest.raises(TeamsAuthenticationError, match="Token expired"):
                verify_jwt_token(token, [mock_key], "test-app-id")
    
    def test_verify_jwt_token_invalid_audience(self):
        """Test JWT token verification with invalid audience."""
        payload = {
            "iss": "https://login.microsoftonline.com/botframework",
            "aud": "wrong-app-id",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time())
        }
        
        secret = "test-secret"
        token = jwt.encode(payload, secret, algorithm="HS256")
        mock_key = {"kty": "RSA", "kid": "test-key"}
        
        with patch("app.bot.auth.jwt.decode") as mock_decode:
            mock_decode.side_effect = jwt.InvalidAudienceError("Invalid audience")
            
            with pytest.raises(TeamsAuthenticationError, match="Invalid audience"):
                verify_jwt_token(token, [mock_key], "test-app-id")
    
    def test_verify_jwt_token_invalid_signature(self):
        """Test JWT token verification with invalid signature."""
        token = "invalid.jwt.token"
        mock_key = {"kty": "RSA", "kid": "test-key"}
        
        with patch("app.bot.auth.jwt.decode") as mock_decode:
            mock_decode.side_effect = jwt.InvalidSignatureError("Invalid signature")
            
            with pytest.raises(TeamsAuthenticationError, match="Invalid signature"):
                verify_jwt_token(token, [mock_key], "test-app-id")
    
    def test_verify_jwt_token_malformed(self):
        """Test JWT token verification with malformed token."""
        token = "not.a.jwt"
        mock_key = {"kty": "RSA", "kid": "test-key"}
        
        with patch("app.bot.auth.jwt.decode") as mock_decode:
            mock_decode.side_effect = jwt.DecodeError("Not a valid JWT")
            
            with pytest.raises(TeamsAuthenticationError, match="Not a valid JWT"):
                verify_jwt_token(token, [mock_key], "test-app-id")
    
    @pytest.mark.asyncio
    async def test_verify_teams_signature_success(self):
        """Test successful Teams signature verification."""
        # Mock valid JWT token in Authorization header
        auth_header = "Bearer valid.jwt.token"
        
        mock_payload = {
            "iss": "https://login.microsoftonline.com/botframework",
            "aud": "test-app-id",
            "exp": int(time.time()) + 3600
        }
        
        with patch("app.bot.auth.get_openid_metadata") as mock_metadata, \
             patch("app.bot.auth.verify_jwt_token") as mock_verify_jwt, \
             patch("app.bot.auth.settings") as mock_settings:
            
            mock_settings.microsoft_app_id = "test-app-id"
            mock_metadata.return_value = {"jwks_uri": "https://login.microsoftonline.com/keys"}
            mock_verify_jwt.return_value = mock_payload
            
            result = await verify_teams_signature(auth_header, {})
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_verify_teams_signature_missing_header(self):
        """Test Teams signature verification with missing auth header."""
        result = await verify_teams_signature(None, {})
        assert result is False
        
        result = await verify_teams_signature("", {})
        assert result is False
    
    @pytest.mark.asyncio
    async def test_verify_teams_signature_invalid_format(self):
        """Test Teams signature verification with invalid header format."""
        # Missing 'Bearer ' prefix
        auth_header = "invalid.jwt.token"
        
        result = await verify_teams_signature(auth_header, {})
        assert result is False
    
    @pytest.mark.asyncio
    async def test_verify_teams_signature_jwt_verification_failure(self):
        """Test Teams signature verification with JWT verification failure."""
        auth_header = "Bearer invalid.jwt.token"
        
        with patch("app.bot.auth.get_openid_metadata") as mock_metadata, \
             patch("app.bot.auth.verify_jwt_token") as mock_verify_jwt, \
             patch("app.bot.auth.settings") as mock_settings:
            
            mock_settings.microsoft_app_id = "test-app-id"
            mock_metadata.return_value = {"jwks_uri": "https://login.microsoftonline.com/keys"}
            mock_verify_jwt.side_effect = TeamsAuthenticationError("Invalid token")
            
            result = await verify_teams_signature(auth_header, {})
            assert result is False
    
    @pytest.mark.asyncio
    async def test_verify_teams_signature_metadata_failure(self):
        """Test Teams signature verification with metadata retrieval failure."""
        auth_header = "Bearer valid.jwt.token"
        
        with patch("app.bot.auth.get_openid_metadata") as mock_metadata:
            mock_metadata.side_effect = TeamsAuthenticationError("Metadata error")
            
            result = await verify_teams_signature(auth_header, {})
            assert result is False
    
    def test_teams_authentication_error(self):
        """Test TeamsAuthenticationError exception."""
        error_message = "Authentication failed"
        error = TeamsAuthenticationError(error_message)
        
        assert str(error) == error_message
        assert isinstance(error, Exception)
    
    @pytest.mark.asyncio
    async def test_verify_teams_signature_service_url_validation(self):
        """Test Teams signature verification with service URL validation."""
        auth_header = "Bearer valid.jwt.token"
        activity = {
            "serviceUrl": "https://smba.trafficmanager.net/teams/"
        }
        
        mock_payload = {
            "iss": "https://login.microsoftonline.com/botframework",
            "aud": "test-app-id",
            "serviceUrl": "https://smba.trafficmanager.net/teams/"
        }
        
        with patch("app.bot.auth.get_openid_metadata") as mock_metadata, \
             patch("app.bot.auth.verify_jwt_token") as mock_verify_jwt, \
             patch("app.bot.auth.settings") as mock_settings:
            
            mock_settings.microsoft_app_id = "test-app-id"
            mock_metadata.return_value = {"jwks_uri": "https://login.microsoftonline.com/keys"}
            mock_verify_jwt.return_value = mock_payload
            
            result = await verify_teams_signature(auth_header, activity)
            assert result is True
    
    @pytest.mark.asyncio
    async def test_verify_teams_signature_invalid_service_url(self):
        """Test Teams signature verification with invalid service URL."""
        auth_header = "Bearer valid.jwt.token"
        activity = {
            "serviceUrl": "https://malicious-site.com/"
        }
        
        mock_payload = {
            "iss": "https://login.microsoftonline.com/botframework",
            "aud": "test-app-id",
            "serviceUrl": "https://smba.trafficmanager.net/teams/"  # Different from activity
        }
        
        with patch("app.bot.auth.get_openid_metadata") as mock_metadata, \
             patch("app.bot.auth.verify_jwt_token") as mock_verify_jwt, \
             patch("app.bot.auth.settings") as mock_settings:
            
            mock_settings.microsoft_app_id = "test-app-id"
            mock_metadata.return_value = {"jwks_uri": "https://login.microsoftonline.com/keys"}
            mock_verify_jwt.return_value = mock_payload
            
            result = await verify_teams_signature(auth_header, activity)
            assert result is False


class TestAuthenticationMiddleware:
    """Test suite for authentication middleware."""
    
    @pytest.fixture
    def auth_middleware(self):
        """Create authentication middleware."""
        return AuthenticationMiddleware()
    
    @pytest.mark.asyncio
    async def test_authentication_middleware_success(self, auth_middleware):
        """Test successful authentication middleware."""
        # Mock request with valid authorization
        mock_request = MagicMock()
        mock_request.headers = {"authorization": "Bearer valid.jwt.token"}
        mock_request.json.return_value = {"type": "message"}
        
        mock_call_next = AsyncMock()
        mock_call_next.return_value = MagicMock(status_code=200)
        
        with patch("app.bot.auth.verify_teams_signature") as mock_verify:
            mock_verify.return_value = True
            
            response = await auth_middleware.dispatch(mock_request, mock_call_next)
            
            assert response.status_code == 200
            mock_call_next.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_authentication_middleware_failure(self, auth_middleware):
        """Test authentication middleware with auth failure."""
        # Mock request with invalid authorization
        mock_request = MagicMock()
        mock_request.headers = {"authorization": "Bearer invalid.token"}
        mock_request.json.return_value = {"type": "message"}
        
        mock_call_next = AsyncMock()
        
        with patch("app.bot.auth.verify_teams_signature") as mock_verify:
            mock_verify.return_value = False
            
            response = await auth_middleware.dispatch(mock_request, mock_call_next)
            
            assert response.status_code == 401
            mock_call_next.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_authentication_middleware_bypass_health(self, auth_middleware):
        """Test authentication middleware bypassing health endpoints."""
        # Mock health check request
        mock_request = MagicMock()
        mock_request.url.path = "/teams/health"
        mock_request.headers = {}
        
        mock_call_next = AsyncMock()
        mock_call_next.return_value = MagicMock(status_code=200)
        
        response = await auth_middleware.dispatch(mock_request, mock_call_next)
        
        assert response.status_code == 200
        mock_call_next.assert_called_once()
        # Should not attempt verification for health endpoints
    
    @pytest.mark.asyncio
    async def test_authentication_middleware_exception_handling(self, auth_middleware):
        """Test authentication middleware exception handling."""
        # Mock request that causes exception
        mock_request = MagicMock()
        mock_request.headers = {"authorization": "Bearer valid.token"}
        mock_request.json.side_effect = Exception("JSON parsing error")
        
        mock_call_next = AsyncMock()
        
        response = await auth_middleware.dispatch(mock_request, mock_call_next)
        
        assert response.status_code == 500
        mock_call_next.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__])