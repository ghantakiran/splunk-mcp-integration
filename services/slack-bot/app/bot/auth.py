"""
Slack authentication and verification utilities.
"""

import hashlib
import hmac
import json
import time
from typing import Dict, Any
from fastapi import Request, HTTPException, Depends
import urllib.parse

from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)

def verify_slack_signature(timestamp: str, body: bytes, signature: str) -> bool:
    """Verify Slack request signature."""
    if abs(time.time() - int(timestamp)) > 60 * 5:
        # Request is older than 5 minutes
        return False
    
    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
    my_signature = 'v0=' + hmac.new(
        settings.slack_signing_secret.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(my_signature, signature)

async def verify_slack_request(request: Request) -> Dict[str, Any]:
    """Verify and parse Slack request."""
    # Get headers
    timestamp = request.headers.get("X-Slack-Request-Timestamp")
    signature = request.headers.get("X-Slack-Signature")
    
    if not timestamp or not signature:
        logger.warning("Missing Slack verification headers")
        raise HTTPException(status_code=401, detail="Missing verification headers")
    
    # Get body
    body = await request.body()
    
    # Verify signature
    if not verify_slack_signature(timestamp, body, signature):
        logger.warning("Invalid Slack signature")
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Parse body based on content type
    content_type = request.headers.get("content-type", "")
    
    if "application/json" in content_type:
        try:
            return json.loads(body.decode('utf-8'))
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON")
    
    elif "application/x-www-form-urlencoded" in content_type:
        try:
            # Parse form data
            parsed_data = urllib.parse.parse_qs(body.decode('utf-8'))
            
            # Handle interactive payloads
            if 'payload' in parsed_data:
                return json.loads(parsed_data['payload'][0])
            
            # Handle regular form data
            return {key: value[0] if len(value) == 1 else value 
                   for key, value in parsed_data.items()}
        except Exception as e:
            logger.error(f"Failed to parse form data: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid form data")
    
    else:
        raise HTTPException(status_code=400, detail="Unsupported content type")

class SlackAuth:
    """Slack authentication utilities."""
    
    @staticmethod
    def get_user_token(user_id: str) -> str:
        """Get user-specific token (placeholder for OAuth implementation)."""
        # This would integrate with OAuth token storage
        # For now, return the bot token
        return settings.slack_bot_token
    
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