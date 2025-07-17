"""
Email utility functions.
"""

import re
import html
from typing import Optional, List, Dict, Any
from email.utils import parseaddr
from urllib.parse import urlparse

from email_validator import validate_email, EmailNotValidError

from app.core.logging import get_logger

logger = get_logger(__name__)


def validate_email_address(email: str) -> bool:
    """Validate email address format."""
    try:
        validate_email(email)
        return True
    except EmailNotValidError:
        return False


def extract_email_domain(email: str) -> Optional[str]:
    """Extract domain from email address."""
    try:
        _, addr = parseaddr(email)
        if '@' in addr:
            return addr.split('@')[1].lower()
        return None
    except Exception:
        return None


def sanitize_email_content(content: str) -> str:
    """Sanitize email content to prevent XSS and other attacks."""
    if not content:
        return ""
    
    # HTML escape
    content = html.escape(content)
    
    # Remove potentially dangerous patterns
    dangerous_patterns = [
        r'<script[^>]*>.*?</script>',
        r'<iframe[^>]*>.*?</iframe>',
        r'javascript:',
        r'vbscript:',
        r'data:text/html',
        r'<object[^>]*>.*?</object>',
        r'<embed[^>]*>.*?</embed>',
    ]
    
    for pattern in dangerous_patterns:
        content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)
    
    return content


def format_email_subject(subject: str, max_length: int = 200) -> str:
    """Format and truncate email subject."""
    if not subject:
        return "No Subject"
    
    # Remove extra whitespace
    subject = ' '.join(subject.split())
    
    # Truncate if too long
    if len(subject) > max_length:
        subject = subject[:max_length - 3] + "..."
    
    return subject


def extract_urls_from_text(text: str) -> List[str]:
    """Extract URLs from text content."""
    url_pattern = re.compile(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    )
    return url_pattern.findall(text)


def is_url_safe(url: str) -> bool:
    """Check if URL is safe to include in emails."""
    try:
        parsed = urlparse(url)
        
        # Only allow http/https
        if parsed.scheme not in ['http', 'https']:
            return False
        
        # Block localhost and private IPs
        if parsed.hostname:
            hostname = parsed.hostname.lower()
            if hostname in ['localhost', '127.0.0.1', '0.0.0.0']:
                return False
            
            # Block private IP ranges
            if hostname.startswith(('10.', '172.', '192.168.')):
                return False
        
        return True
    except Exception:
        return False


def parse_email_headers(headers: Dict[str, str]) -> Dict[str, Any]:
    """Parse and extract useful information from email headers."""
    parsed = {}
    
    # Extract standard headers
    standard_headers = [
        'from', 'to', 'cc', 'bcc', 'subject', 'date',
        'message-id', 'in-reply-to', 'references'
    ]
    
    for header in standard_headers:
        value = headers.get(header) or headers.get(header.title())
        if value:
            parsed[header] = value
    
    # Extract custom headers
    custom_headers = {}
    for key, value in headers.items():
        if key.lower().startswith('x-'):
            custom_headers[key] = value
    
    if custom_headers:
        parsed['custom_headers'] = custom_headers
    
    return parsed


def generate_message_id(domain: str = "splunk-mcp.local") -> str:
    """Generate a unique message ID for email."""
    import uuid
    from datetime import datetime
    
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    unique_id = str(uuid.uuid4()).replace('-', '')
    
    return f"<{timestamp}.{unique_id}@{domain}>"


def parse_email_list(email_list: str) -> List[str]:
    """Parse comma-separated email list."""
    if not email_list:
        return []
    
    emails = []
    for email in email_list.split(','):
        email = email.strip()
        if email and validate_email_address(email):
            emails.append(email)
    
    return emails


def format_email_display_name(name: str, email: str) -> str:
    """Format display name for email."""
    if not name:
        return email
    
    # Sanitize name
    name = re.sub(r'[<>"]', '', name).strip()
    
    if not name:
        return email
    
    return f'"{name}" <{email}>'


def extract_query_from_email_body(body: str) -> Optional[str]:
    """Extract Splunk query from email body."""
    if not body:
        return None
    
    # Look for common query indicators
    query_patterns = [
        r'query:\s*(.+?)(?:\n|$)',
        r'search:\s*(.+?)(?:\n|$)',
        r'spl:\s*(.+?)(?:\n|$)',
        r'```\s*(.+?)\s*```',
        r'show me\s+(.+?)(?:\n|$)',
        r'find\s+(.+?)(?:\n|$)',
        r'get\s+(.+?)(?:\n|$)',
    ]
    
    for pattern in query_patterns:
        matches = re.findall(pattern, body, re.IGNORECASE | re.DOTALL)
        if matches:
            query = matches[0].strip()
            if len(query) > 10:  # Minimum query length
                return query
    
    # If no specific pattern found, check if the entire body looks like a query
    body_clean = body.strip()
    if (len(body_clean) > 10 and 
        any(keyword in body_clean.lower() for keyword in ['search', 'index=', 'source=', 'sourcetype=', '|', 'stats', 'eval', 'where'])):
        return body_clean
    
    return None


def is_auto_reply_email(headers: Dict[str, str], subject: str) -> bool:
    """Check if email is an auto-reply/vacation message."""
    # Check for auto-reply headers
    auto_reply_headers = [
        'auto-submitted',
        'x-auto-response-suppress',
        'x-autorespond',
        'x-autoreply',
    ]
    
    for header in auto_reply_headers:
        if headers.get(header) or headers.get(header.title()):
            return True
    
    # Check subject for auto-reply indicators
    auto_reply_subjects = [
        'auto-reply', 'automatic reply', 'out of office', 'vacation',
        'away message', 'delivery status notification', 'undelivered',
        'mail delivery failed', 'returned mail', 'bounced'
    ]
    
    subject_lower = subject.lower()
    return any(indicator in subject_lower for indicator in auto_reply_subjects)


def clean_email_body_for_processing(body: str) -> str:
    """Clean email body for query processing."""
    if not body:
        return ""
    
    # Remove email signatures
    signature_patterns = [
        r'\n--\s*\n.*',
        r'\n-+\s*\n.*',
        r'\nSent from my .*',
        r'\nGet Outlook for .*',
        r'\n\[.*\]$',
    ]
    
    for pattern in signature_patterns:
        body = re.sub(pattern, '', body, flags=re.DOTALL)
    
    # Remove quoted text
    quoted_patterns = [
        r'\n>.*',
        r'\nOn .* wrote:.*',
        r'\nFrom:.*\nTo:.*',
        r'\n_{10,}.*',
    ]
    
    for pattern in quoted_patterns:
        body = re.sub(pattern, '', body, flags=re.DOTALL)
    
    # Clean up whitespace
    body = re.sub(r'\n\s*\n', '\n\n', body)
    body = body.strip()
    
    return body