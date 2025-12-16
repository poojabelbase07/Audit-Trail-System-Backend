"""
Core Package - Configuration, security, and dependencies

This package contains:
- config.py: Application configuration and settings
- security.py: Password hashing and JWT token management
- dependencies.py: FastAPI dependency injection functions
"""

from app.core.config import settings, get_settings  # Export settings for easy import
from app.core.security import hash_password, verify_password, create_access_token, decode_token
from app.core.dependencies import get_current_user, get_current_admin_user, get_optional_user

# Export commonly used functions
__all__ = [
    "settings",
    "get_settings",
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_token",
    "get_current_user",
    "get_current_admin_user",
    "get_optional_user",
]