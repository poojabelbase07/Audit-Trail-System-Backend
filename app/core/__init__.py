"""
Core Package - Configuration, security, and dependencies

IMPORTANT: Only import config and security here.
Dependencies must be imported directly to avoid circular imports.
"""

from app.core.config import settings, get_settings
from app.core.security import hash_password, verify_password, create_access_token, decode_token

__all__ = [
    "settings",
    "get_settings",
    "hash_password", 
    "verify_password",
    "create_access_token",
    "decode_token",
]