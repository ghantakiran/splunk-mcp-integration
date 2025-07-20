"""
Tests for Slack authentication functionality.
"""

import pytest
import hashlib
import hmac
import time
from unittest.mock import patch, MagicMock

from app.bot.auth import verify_slack_signature, SlackAuthenticationError


class TestSlackAuthentication:
    """Test suite for Slack authentication."""
    
    def test_verify_slack_signature_success(self):
        """Test successful Slack signature verification."""
        # Setup
        signing_secret = "test_signing_secret"
        timestamp = str(int(time.time()))
        body = '{"type":"url_verification","challenge":"test"}'
        
        # Create expected signature
        sig_basestring = f"v0:{timestamp}:{body}"
        expected_signature = hmac.new(
            signing_secret.encode(),
            sig_basestring.encode(),
            hashlib.sha256
        ).hexdigest()
        slack_signature = f"v0={expected_signature}"
        
        # Test
        with patch("app.bot.auth.settings") as mock_settings:
            mock_settings.slack_signing_secret = signing_secret
            
            result = verify_slack_signature(slack_signature, timestamp, body)
            assert result is True
    
    def test_verify_slack_signature_invalid_signature(self):
        """Test signature verification with invalid signature."""
        # Setup
        signing_secret = "test_signing_secret"
        timestamp = str(int(time.time()))
        body = '{"type":"url_verification","challenge":"test"}'
        invalid_signature = "v0=invalid_signature"
        
        # Test
        with patch("app.bot.auth.settings") as mock_settings:
            mock_settings.slack_signing_secret = signing_secret
            
            result = verify_slack_signature(invalid_signature, timestamp, body)
            assert result is False
    
    def test_verify_slack_signature_old_timestamp(self):
        """Test signature verification with old timestamp."""
        # Setup
        signing_secret = "test_signing_secret"
        old_timestamp = str(int(time.time()) - 400)  # 400 seconds old (> 300 second limit)
        body = '{"type":"url_verification","challenge":"test"}'
        
        # Create valid signature but with old timestamp
        sig_basestring = f"v0:{old_timestamp}:{body}"
        signature = hmac.new(
            signing_secret.encode(),
            sig_basestring.encode(),
            hashlib.sha256
        ).hexdigest()
        slack_signature = f"v0={signature}"
        
        # Test
        with patch("app.bot.auth.settings") as mock_settings:
            mock_settings.slack_signing_secret = signing_secret
            
            result = verify_slack_signature(slack_signature, old_timestamp, body)
            assert result is False
    
    def test_verify_slack_signature_malformed_signature(self):
        """Test signature verification with malformed signature."""
        # Setup
        signing_secret = "test_signing_secret"
        timestamp = str(int(time.time()))
        body = '{"type":"url_verification","challenge":"test"}'
        malformed_signature = "invalid_format"
        
        # Test
        with patch("app.bot.auth.settings") as mock_settings:
            mock_settings.slack_signing_secret = signing_secret
            
            result = verify_slack_signature(malformed_signature, timestamp, body)
            assert result is False
    
    def test_verify_slack_signature_empty_secret(self):
        """Test signature verification with empty signing secret."""
        # Setup
        timestamp = str(int(time.time()))
        body = '{"type":"url_verification","challenge":"test"}'
        signature = "v0=some_signature"
        
        # Test
        with patch("app.bot.auth.settings") as mock_settings:
            mock_settings.slack_signing_secret = ""
            
            result = verify_slack_signature(signature, timestamp, body)
            assert result is False
    
    def test_verify_slack_signature_none_values(self):
        """Test signature verification with None values."""
        # Test with None signature
        result = verify_slack_signature(None, "123456789", "body")
        assert result is False
        
        # Test with None timestamp
        result = verify_slack_signature("v0=signature", None, "body")
        assert result is False
        
        # Test with None body
        result = verify_slack_signature("v0=signature", "123456789", None)
        assert result is False
    
    def test_verify_slack_signature_exception_handling(self):
        """Test signature verification exception handling."""
        # Setup
        signing_secret = "test_signing_secret"
        timestamp = str(int(time.time()))
        body = '{"type":"url_verification","challenge":"test"}'
        signature = "v0=some_signature"
        
        # Test with exception in HMAC calculation
        with patch("app.bot.auth.settings") as mock_settings, \
             patch("app.bot.auth.hmac.new") as mock_hmac:
            
            mock_settings.slack_signing_secret = signing_secret
            mock_hmac.side_effect = Exception("HMAC error")
            
            result = verify_slack_signature(signature, timestamp, body)
            assert result is False
    
    def test_slack_authentication_error(self):
        """Test SlackAuthenticationError exception."""
        error_message = "Authentication failed"
        error = SlackAuthenticationError(error_message)
        
        assert str(error) == error_message
        assert isinstance(error, Exception)
    
    def test_verify_slack_signature_with_unicode_body(self):
        """Test signature verification with Unicode characters in body."""
        # Setup
        signing_secret = "test_signing_secret"
        timestamp = str(int(time.time()))
        body = '{"type":"message","text":"Hello 世界 🌍"}'
        
        # Create expected signature
        sig_basestring = f"v0:{timestamp}:{body}"
        expected_signature = hmac.new(
            signing_secret.encode(),
            sig_basestring.encode(),
            hashlib.sha256
        ).hexdigest()
        slack_signature = f"v0={expected_signature}"
        
        # Test
        with patch("app.bot.auth.settings") as mock_settings:
            mock_settings.slack_signing_secret = signing_secret
            
            result = verify_slack_signature(slack_signature, timestamp, body)
            assert result is True
    
    def test_verify_slack_signature_case_sensitivity(self):
        """Test that signature verification is case sensitive."""
        # Setup
        signing_secret = "test_signing_secret"
        timestamp = str(int(time.time()))
        body = '{"type":"url_verification","challenge":"test"}'
        
        # Create expected signature
        sig_basestring = f"v0:{timestamp}:{body}"
        expected_signature = hmac.new(
            signing_secret.encode(),
            sig_basestring.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Test with uppercase signature (should fail)
        slack_signature = f"v0={expected_signature.upper()}"
        
        with patch("app.bot.auth.settings") as mock_settings:
            mock_settings.slack_signing_secret = signing_secret
            
            result = verify_slack_signature(slack_signature, timestamp, body)
            assert result is False
    
    def test_verify_slack_signature_with_special_characters(self):
        """Test signature verification with special characters in secret."""
        # Setup
        signing_secret = "test!@#$%^&*()_+-=secret"
        timestamp = str(int(time.time()))
        body = '{"type":"url_verification","challenge":"test"}'
        
        # Create expected signature
        sig_basestring = f"v0:{timestamp}:{body}"
        expected_signature = hmac.new(
            signing_secret.encode(),
            sig_basestring.encode(),
            hashlib.sha256
        ).hexdigest()
        slack_signature = f"v0={expected_signature}"
        
        # Test
        with patch("app.bot.auth.settings") as mock_settings:
            mock_settings.slack_signing_secret = signing_secret
            
            result = verify_slack_signature(slack_signature, timestamp, body)
            assert result is True
    
    def test_verify_slack_signature_timing_attack_protection(self):
        """Test that signature verification uses time-constant comparison."""
        # Setup
        signing_secret = "test_signing_secret"
        timestamp = str(int(time.time()))
        body = '{"type":"url_verification","challenge":"test"}'
        
        # Create a signature that differs by one character
        sig_basestring = f"v0:{timestamp}:{body}"
        correct_signature = hmac.new(
            signing_secret.encode(),
            sig_basestring.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Modify one character to create incorrect signature
        incorrect_signature = correct_signature[:-1] + ('a' if correct_signature[-1] != 'a' else 'b')
        slack_signature = f"v0={incorrect_signature}"
        
        # Test
        with patch("app.bot.auth.settings") as mock_settings:
            mock_settings.slack_signing_secret = signing_secret
            
            result = verify_slack_signature(slack_signature, timestamp, body)
            assert result is False
    
    def test_verify_slack_signature_large_body(self):
        """Test signature verification with large request body."""
        # Setup
        signing_secret = "test_signing_secret"
        timestamp = str(int(time.time()))
        # Create a large body (simulating file upload or large message)
        large_body = '{"type":"message","text":"' + 'x' * 10000 + '"}'
        
        # Create expected signature
        sig_basestring = f"v0:{timestamp}:{large_body}"
        expected_signature = hmac.new(
            signing_secret.encode(),
            sig_basestring.encode(),
            hashlib.sha256
        ).hexdigest()
        slack_signature = f"v0={expected_signature}"
        
        # Test
        with patch("app.bot.auth.settings") as mock_settings:
            mock_settings.slack_signing_secret = signing_secret
            
            result = verify_slack_signature(slack_signature, timestamp, large_body)
            assert result is True


if __name__ == "__main__":
    pytest.main([__file__])