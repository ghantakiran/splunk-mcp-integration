"""
Security utilities for authentication and authorization
"""

from datetime import datetime, timedelta
from typing import Optional, Union, Any, Dict
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Request
import secrets
import hashlib
from .config import settings


# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Token handler
security = HTTPBearer()


class SecurityManager:
    """Security manager for authentication and authorization"""
    
    def __init__(self):
        self.secret_key = settings.secret_key
        self.algorithm = settings.jwt_algorithm
        self.access_token_expire_minutes = settings.jwt_expire_minutes
        self.refresh_token_expire_days = settings.jwt_refresh_expire_days
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plain password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Generate password hash"""
        return pwd_context.hash(password)
    
    def create_access_token(
        self, 
        data: Dict[str, Any], 
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({
            "exp": expire,
            "type": "access",
            "iat": datetime.utcnow()
        })
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(
        self, 
        data: Dict[str, Any], 
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        
        to_encode.update({
            "exp": expire,
            "type": "refresh",
            "iat": datetime.utcnow()
        })
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError:
            return None
    
    def extract_token_from_credentials(
        self, 
        credentials: HTTPAuthorizationCredentials
    ) -> str:
        """Extract token from authorization credentials"""
        if credentials.scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return credentials.credentials
    
    def generate_session_token(self) -> str:
        """Generate secure session token"""
        return secrets.token_urlsafe(32)
    
    def generate_api_key(self, user_id: str) -> str:
        """Generate API key for user"""
        timestamp = str(int(datetime.utcnow().timestamp()))
        raw_key = f"{user_id}:{timestamp}:{secrets.token_urlsafe(16)}"
        return hashlib.sha256(raw_key.encode()).hexdigest()
    
    def hash_api_key(self, api_key: str) -> str:
        """Hash API key for storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    def validate_password_strength(self, password: str) -> Dict[str, Any]:
        """Validate password strength"""
        errors = []
        score = 0
        
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long")
        else:
            score += 1
        
        if not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")
        else:
            score += 1
        
        if not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")
        else:
            score += 1
        
        if not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one digit")
        else:
            score += 1
        
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            errors.append("Password must contain at least one special character")
        else:
            score += 1
        
        strength_levels = ["Very Weak", "Weak", "Fair", "Good", "Strong"]
        strength = strength_levels[min(score, len(strength_levels) - 1)]
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "strength": strength,
            "score": score
        }


# Global security manager instance
security_manager = SecurityManager()


# Convenience functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password"""
    return security_manager.verify_password(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password"""
    return security_manager.get_password_hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create access token"""
    return security_manager.create_access_token(data, expires_delta)


def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create refresh token"""
    return security_manager.create_refresh_token(data, expires_delta)


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify token"""
    return security_manager.verify_token(token)