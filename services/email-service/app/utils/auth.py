"""
Authentication utilities for Email Service.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional

import jwt
from jose import JWTError

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def create_jwt_token(user_id: str, additional_claims: Optional[Dict[str, Any]] = None) -> str:
    """Create a JWT token for a user."""
    now = datetime.utcnow()
    expire = now + timedelta(hours=settings.jwt_expiration_hours)
    
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": expire,
        "iss": "email-service",
        "aud": "splunk-mcp",
    }
    
    if additional_claims:
        payload.update(additional_claims)
    
    try:
        token = jwt.encode(
            payload,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )
        return token
    except Exception as e:
        logger.error("Failed to create JWT token", error=str(e))
        raise


def verify_jwt_token(token: str) -> Dict[str, Any]:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            audience="splunk-mcp",
            issuer="email-service",
        )
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token has expired")
        raise JWTError("Token has expired")
    except jwt.InvalidTokenError as e:
        logger.warning("Invalid JWT token", error=str(e))
        raise JWTError("Invalid token")
    except Exception as e:
        logger.error("JWT token verification failed", error=str(e))
        raise JWTError("Token verification failed")


def extract_user_id_from_token(token: str) -> Optional[str]:
    """Extract user ID from JWT token without full validation."""
    try:
        # Decode without verification for user ID extraction
        payload = jwt.decode(token, options={"verify_signature": False})
        return payload.get("sub")
    except Exception:
        return None


def is_token_expired(token: str) -> bool:
    """Check if JWT token is expired."""
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        exp = payload.get("exp")
        if exp:
            return datetime.utcnow() > datetime.fromtimestamp(exp)
        return True
    except Exception:
        return True


def get_token_claims(token: str) -> Dict[str, Any]:
    """Get claims from JWT token without verification."""
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        return payload
    except Exception:
        return {}