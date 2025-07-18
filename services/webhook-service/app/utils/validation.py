"""
Validation utilities for Webhook Service.
"""

import re
import urllib.parse
from typing import Dict, List, Any
from urllib.parse import urlparse

from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)


async def validate_webhook_url(url: str) -> None:
    """Validate webhook URL."""
    try:
        parsed = urlparse(url)
        
        # Check scheme
        if parsed.scheme not in settings.webhook_url_schemes:
            raise ValueError(f"Invalid URL scheme: {parsed.scheme}")
        
        # Check hostname
        if not parsed.hostname:
            raise ValueError("URL must have a hostname")
        
        # Check for localhost/private IPs in production
        if settings.environment == "production":
            await _validate_production_url(parsed)
        
        # Check domain restrictions
        if settings.allowed_webhook_domains:
            if parsed.hostname not in settings.allowed_webhook_domains:
                raise ValueError(f"Domain not allowed: {parsed.hostname}")
        
        if settings.blocked_webhook_domains:
            if parsed.hostname in settings.blocked_webhook_domains:
                raise ValueError(f"Domain is blocked: {parsed.hostname}")
        
    except Exception as e:
        logger.error(f"Webhook URL validation failed: {e}")
        raise


async def _validate_production_url(parsed_url) -> None:
    """Validate URL for production environment."""
    hostname = parsed_url.hostname
    
    # Block localhost
    if hostname in ["localhost", "127.0.0.1", "::1"]:
        raise ValueError("Localhost URLs not allowed in production")
    
    # Block private IP ranges
    import ipaddress
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            raise ValueError("Private IP addresses not allowed in production")
    except ValueError:
        # Not an IP address, continue with domain validation
        pass


def validate_webhook_headers(headers: Dict[str, str]) -> None:
    """Validate webhook headers."""
    if not isinstance(headers, dict):
        raise ValueError("Headers must be a dictionary")
    
    # Check header count limit
    if len(headers) > 20:
        raise ValueError("Too many headers (max 20)")
    
    # Validate each header
    for key, value in headers.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise ValueError("Header keys and values must be strings")
        
        # Check header name
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9-_]*$', key):
            raise ValueError(f"Invalid header name: {key}")
        
        # Check header value length
        if len(value) > 1000:
            raise ValueError(f"Header value too long: {key}")
        
        # Block dangerous headers
        dangerous_headers = [
            "authorization",
            "cookie",
            "set-cookie",
            "x-forwarded-for",
            "x-real-ip",
        ]
        if key.lower() in dangerous_headers:
            raise ValueError(f"Header not allowed: {key}")


def validate_event_payload(payload: Dict[str, Any]) -> None:
    """Validate event payload."""
    if not isinstance(payload, dict):
        raise ValueError("Payload must be a dictionary")
    
    # Check payload size
    import json
    payload_size = len(json.dumps(payload))
    if payload_size > settings.max_webhook_payload_size:
        raise ValueError(f"Payload too large: {payload_size} bytes")
    
    # Check for dangerous content
    _check_dangerous_content(payload)


def _check_dangerous_content(obj: Any, path: str = "") -> None:
    """Recursively check for dangerous content in payload."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            new_path = f"{path}.{key}" if path else key
            _check_dangerous_content(value, new_path)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            new_path = f"{path}[{i}]" if path else f"[{i}]"
            _check_dangerous_content(item, new_path)
    elif isinstance(obj, str):
        # Check for script injection
        dangerous_patterns = [
            r'<script[^>]*>',
            r'javascript:',
            r'data:text/html',
            r'vbscript:',
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, obj, re.IGNORECASE):
                raise ValueError(f"Dangerous content detected at {path}")


def validate_event_filters(filters: Dict[str, Any]) -> None:
    """Validate event filters."""
    if not isinstance(filters, dict):
        raise ValueError("Event filters must be a dictionary")
    
    # Check filter count
    if len(filters) > 10:
        raise ValueError("Too many event filters (max 10)")
    
    # Validate each filter
    for key, value in filters.items():
        if not isinstance(key, str):
            raise ValueError("Filter keys must be strings")
        
        if len(key) > 100:
            raise ValueError(f"Filter key too long: {key}")
        
        # Value can be string, number, boolean, or list
        if not isinstance(value, (str, int, float, bool, list)):
            raise ValueError(f"Invalid filter value type for {key}")
        
        if isinstance(value, list):
            if len(value) > 50:
                raise ValueError(f"Filter value list too long for {key}")


def validate_endpoint_name(name: str) -> None:
    """Validate endpoint name."""
    if not isinstance(name, str):
        raise ValueError("Endpoint name must be a string")
    
    if len(name.strip()) == 0:
        raise ValueError("Endpoint name cannot be empty")
    
    if len(name) > 255:
        raise ValueError("Endpoint name too long (max 255 characters)")
    
    # Check for valid characters
    if not re.match(r'^[a-zA-Z0-9\s\-_\.]+$', name):
        raise ValueError("Endpoint name contains invalid characters")


def validate_endpoint_description(description: str) -> None:
    """Validate endpoint description."""
    if description is None:
        return
    
    if not isinstance(description, str):
        raise ValueError("Endpoint description must be a string")
    
    if len(description) > 1000:
        raise ValueError("Endpoint description too long (max 1000 characters)")


def validate_webhook_secret(secret: str) -> None:
    """Validate webhook secret."""
    if not isinstance(secret, str):
        raise ValueError("Webhook secret must be a string")
    
    if len(secret) < 8:
        raise ValueError("Webhook secret too short (min 8 characters)")
    
    if len(secret) > 255:
        raise ValueError("Webhook secret too long (max 255 characters)")
    
    # Check for reasonable complexity
    has_upper = any(c.isupper() for c in secret)
    has_lower = any(c.islower() for c in secret)
    has_digit = any(c.isdigit() for c in secret)
    has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in secret)
    
    complexity_count = sum([has_upper, has_lower, has_digit, has_special])
    if complexity_count < 2:
        raise ValueError("Webhook secret must contain at least 2 of: uppercase, lowercase, digits, special characters")