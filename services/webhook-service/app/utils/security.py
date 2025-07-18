"""
Security utilities for Webhook Service.
"""

import secrets
import string
import hmac
import hashlib
from typing import Optional

from ..core.logging import get_logger

logger = get_logger(__name__)


def generate_webhook_secret(length: int = 32) -> str:
    """Generate a secure webhook secret."""
    # Use a mix of alphanumeric and special characters
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    secret = ''.join(secrets.choice(alphabet) for _ in range(length))
    return secret


def validate_webhook_secret(secret: str) -> bool:
    """Validate webhook secret strength."""
    if len(secret) < 8:
        return False
    
    # Check for minimum complexity
    has_upper = any(c.isupper() for c in secret)
    has_lower = any(c.islower() for c in secret)
    has_digit = any(c.isdigit() for c in secret)
    has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in secret)
    
    complexity_count = sum([has_upper, has_lower, has_digit, has_special])
    return complexity_count >= 2


def generate_signature(payload: str, secret: str) -> str:
    """Generate HMAC-SHA256 signature for webhook payload."""
    signature = hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return f"sha256={signature}"


def verify_signature(payload: str, signature: str, secret: str) -> bool:
    """Verify webhook signature."""
    try:
        expected_signature = generate_signature(payload, secret)
        return hmac.compare_digest(signature, expected_signature)
    except Exception as e:
        logger.error(f"Signature verification failed: {e}")
        return False


def sanitize_header_value(value: str) -> str:
    """Sanitize header value to prevent injection attacks."""
    # Remove control characters and normalize whitespace
    sanitized = ''.join(char for char in value if ord(char) >= 32 or char in '\t\n\r')
    sanitized = ' '.join(sanitized.split())
    return sanitized[:1000]  # Limit length


def sanitize_url(url: str) -> str:
    """Sanitize URL to prevent injection attacks."""
    # Basic URL sanitization
    sanitized = url.strip()
    
    # Remove dangerous protocols
    dangerous_protocols = ['javascript:', 'data:', 'vbscript:', 'file:']
    for protocol in dangerous_protocols:
        if sanitized.lower().startswith(protocol):
            raise ValueError(f"Dangerous protocol not allowed: {protocol}")
    
    return sanitized


def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    import bcrypt
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash."""
    import bcrypt
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False


def generate_api_key(length: int = 32) -> str:
    """Generate a secure API key."""
    return secrets.token_urlsafe(length)


def is_safe_redirect_url(url: str, allowed_hosts: list = None) -> bool:
    """Check if redirect URL is safe."""
    from urllib.parse import urlparse
    
    try:
        parsed = urlparse(url)
        
        # Must be absolute URL
        if not parsed.netloc:
            return False
        
        # Check allowed hosts
        if allowed_hosts and parsed.hostname not in allowed_hosts:
            return False
        
        # Block dangerous schemes
        if parsed.scheme not in ['http', 'https']:
            return False
        
        return True
        
    except Exception:
        return False


class SecurityHeaders:
    """Security headers for HTTP responses."""
    
    @staticmethod
    def get_security_headers() -> dict:
        """Get recommended security headers."""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none'"
            ),
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": (
                "geolocation=(), "
                "microphone=(), "
                "camera=(), "
                "payment=(), "
                "usb=(), "
                "magnetometer=(), "
                "gyroscope=(), "
                "speaker=()"
            )
        }


def mask_sensitive_data(data: str, mask_char: str = "*", visible_chars: int = 4) -> str:
    """Mask sensitive data for logging."""
    if not data or len(data) <= visible_chars:
        return mask_char * len(data) if data else ""
    
    visible_part = data[:visible_chars]
    masked_part = mask_char * (len(data) - visible_chars)
    return visible_part + masked_part


def validate_content_type(content_type: str) -> bool:
    """Validate content type for webhook requests."""
    allowed_types = [
        "application/json",
        "application/x-www-form-urlencoded",
        "text/plain"
    ]
    
    # Extract base content type (ignore charset, etc.)
    base_type = content_type.split(';')[0].strip().lower()
    return base_type in allowed_types