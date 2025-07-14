"""
API versioning middleware and utilities
"""

import re
from typing import Optional, Tuple
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from .config import settings
from .logging import get_logger

logger = get_logger(__name__)


class APIVersionMiddleware(BaseHTTPMiddleware):
    """Middleware to handle API versioning"""
    
    def __init__(self, app, supported_versions: list = None):
        super().__init__(app)
        self.supported_versions = supported_versions or ["1.0.0"]
        self.current_version = "1.0.0"
        
    async def dispatch(self, request: Request, call_next):
        """Process request and add version information"""
        
        # Extract version from URL path
        version_info = self.extract_version_from_path(request.url.path)
        
        if version_info:
            version, clean_path = version_info
            
            # Validate version
            if not self.is_version_supported(version):
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "error": {
                            "message": f"API version '{version}' is not supported",
                            "code": "unsupported_version",
                            "details": {
                                "supported_versions": self.supported_versions,
                                "current_version": self.current_version
                            }
                        }
                    }
                )
            
            # Add version info to request state
            request.state.api_version = version
            request.state.clean_path = clean_path
        else:
            # Default to current version for non-versioned paths
            request.state.api_version = self.current_version
            request.state.clean_path = request.url.path
        
        # Process request
        response = await call_next(request)
        
        # Add version headers to response
        if hasattr(request.state, 'api_version'):
            response.headers["X-API-Version"] = request.state.api_version
            response.headers["X-API-Current-Version"] = self.current_version
            response.headers["X-API-Supported-Versions"] = ",".join(self.supported_versions)
        
        return response
    
    def extract_version_from_path(self, path: str) -> Optional[Tuple[str, str]]:
        """Extract version from URL path"""
        # Pattern to match /api/v1/ or /api/v1.0/ or /api/v1.0.0/
        version_pattern = r'^/api/v(\d+(?:\.\d+)*)'
        
        match = re.match(version_pattern, path)
        if match:
            version_part = match.group(1)
            
            # Normalize version (e.g., "1" -> "1.0.0")
            version = self.normalize_version(version_part)
            
            # Remove version from path for internal routing
            clean_path = re.sub(version_pattern, '/api', path)
            
            return version, clean_path
        
        return None
    
    def normalize_version(self, version: str) -> str:
        """Normalize version string to semantic version format"""
        parts = version.split('.')
        
        # Pad with zeros to make it semantic version
        while len(parts) < 3:
            parts.append('0')
        
        return '.'.join(parts[:3])
    
    def is_version_supported(self, version: str) -> bool:
        """Check if version is supported"""
        return version in self.supported_versions


class VersionExtractor:
    """Utility class for extracting version information from requests"""
    
    @staticmethod
    def get_version_from_header(request: Request) -> Optional[str]:
        """Extract version from Accept header"""
        accept_header = request.headers.get("Accept", "")
        
        # Look for version in Accept header like: application/vnd.api+json;version=1.0.0
        version_pattern = r'version=(\d+(?:\.\d+)*)'
        match = re.search(version_pattern, accept_header)
        
        if match:
            return match.group(1)
        
        return None
    
    @staticmethod
    def get_version_from_query(request: Request) -> Optional[str]:
        """Extract version from query parameter"""
        return request.query_params.get("version") or request.query_params.get("v")
    
    @staticmethod
    def get_version_from_custom_header(request: Request) -> Optional[str]:
        """Extract version from custom header"""
        return request.headers.get("X-API-Version") or request.headers.get("API-Version")
    
    @staticmethod
    def get_request_version(request: Request) -> Optional[str]:
        """Get version from request using multiple methods"""
        # Priority order: URL path > Custom header > Accept header > Query parameter
        
        # URL path (handled by middleware)
        if hasattr(request.state, 'api_version'):
            return request.state.api_version
        
        # Custom header
        version = VersionExtractor.get_version_from_custom_header(request)
        if version:
            return version
        
        # Accept header
        version = VersionExtractor.get_version_from_header(request)
        if version:
            return version
        
        # Query parameter
        version = VersionExtractor.get_version_from_query(request)
        if version:
            return version
        
        return None


class VersionValidator:
    """Utility class for version validation"""
    
    @staticmethod
    def validate_version_format(version: str) -> bool:
        """Validate version format (semantic versioning)"""
        pattern = r'^\d+\.\d+\.\d+(?:-[a-zA-Z0-9\-\.]+)?(?:\+[a-zA-Z0-9\-\.]+)?$'
        return bool(re.match(pattern, version))
    
    @staticmethod
    def compare_versions(version1: str, version2: str) -> int:
        """Compare two versions. Returns -1, 0, or 1"""
        def version_tuple(v):
            return tuple(map(int, v.split('.')))
        
        v1_tuple = version_tuple(version1)
        v2_tuple = version_tuple(version2)
        
        if v1_tuple < v2_tuple:
            return -1
        elif v1_tuple > v2_tuple:
            return 1
        else:
            return 0
    
    @staticmethod
    def is_version_deprecated(version: str, current_version: str) -> bool:
        """Check if a version is deprecated"""
        # For this implementation, consider versions more than 1 major version behind as deprecated
        try:
            current_major = int(current_version.split('.')[0])
            version_major = int(version.split('.')[0])
            
            return (current_major - version_major) > 1
        except (ValueError, IndexError):
            return False


def get_deprecation_warning(version: str, current_version: str) -> Optional[str]:
    """Get deprecation warning message for a version"""
    if VersionValidator.is_version_deprecated(version, current_version):
        return f"API version {version} is deprecated. Please migrate to version {current_version}."
    
    return None


def add_version_headers(response: Response, request: Request, current_version: str = "1.0.0"):
    """Add version-related headers to response"""
    version = getattr(request.state, 'api_version', current_version)
    
    response.headers["X-API-Version"] = version
    response.headers["X-API-Current-Version"] = current_version
    
    # Add deprecation warning if applicable
    warning = get_deprecation_warning(version, current_version)
    if warning:
        response.headers["X-API-Deprecation-Warning"] = warning
        response.headers["Warning"] = f'299 - "Deprecated API version"'
    
    return response


class APIVersionConfig:
    """Configuration for API versioning"""
    
    SUPPORTED_VERSIONS = ["1.0.0"]
    CURRENT_VERSION = "1.0.0"
    DEFAULT_VERSION = "1.0.0"
    
    # Version-specific configurations
    VERSION_CONFIGS = {
        "1.0.0": {
            "prefix": "/api/v1",
            "deprecated": False,
            "sunset_date": None,
            "migration_guide": "https://github.com/ghantakiran/splunk-mcp-integration/blob/main/docs/api/v1.md"
        }
    }
    
    @classmethod
    def get_version_config(cls, version: str) -> dict:
        """Get configuration for a specific version"""
        return cls.VERSION_CONFIGS.get(version, {})
    
    @classmethod
    def is_version_supported(cls, version: str) -> bool:
        """Check if version is supported"""
        return version in cls.SUPPORTED_VERSIONS
    
    @classmethod
    def get_version_info(cls) -> dict:
        """Get comprehensive version information"""
        return {
            "current_version": cls.CURRENT_VERSION,
            "default_version": cls.DEFAULT_VERSION,
            "supported_versions": cls.SUPPORTED_VERSIONS,
            "version_configs": cls.VERSION_CONFIGS
        }