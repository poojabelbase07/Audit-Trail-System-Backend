"""
FastAPI Dependencies - Reusable dependency injection functions
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.database import get_db
from app.core.security import decode_token
from app.models import User, UserRole

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme - expects "Authorization: Bearer <token>" header
security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),  # Extract token from Authorization header
    db: Session = Depends(get_db)  # Get database session
) -> User:
    """
    Dependency to get currently authenticated user from JWT token.
    
    Process:
        1. Extract token from Authorization header
        2. Verify token signature and expiration
        3. Extract user ID from token payload
        4. Fetch user from database
        5. Verify user is active
        
    Returns:
        User object if authenticated
        
    Raises:
        HTTPException 401: If token invalid, expired, or user not found
        
    Usage in endpoints:
        @app.get("/protected")
        def protected_route(current_user: User = Depends(get_current_user)):
            return {"user": current_user.email}
    """
    # Extract token from credentials
    token = credentials.credentials  # Bearer token value
    
    # Decode and verify token
    user_id = decode_token(token)  # Returns user ID or None
    if not user_id:
        logger.warning("⚠️  Invalid or expired token provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},  # Tell client to use Bearer auth
        )
    
    # Fetch user from database
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.warning(f"⚠️  Token valid but user {user_id} not found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    # Check if user account is active
    if not user.is_active:
        logger.warning(f"⚠️  Inactive user {user.email} attempted access")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
    
    logger.debug(f"✅ Authenticated user: {user.email}")
    return user  # Return user object for use in endpoint

def get_current_active_user(
    current_user: User = Depends(get_current_user)  # Reuse get_current_user dependency
) -> User:
    """
    Dependency that ensures user is active.
    Already handled by get_current_user, but kept for explicit semantics.
    
    Usage:
        @app.get("/profile")
        def get_profile(user: User = Depends(get_current_active_user)):
            return user
    """
    return current_user  # get_current_user already checks is_active

def get_current_admin_user(
    current_user: User = Depends(get_current_user)  # Get authenticated user
) -> User:
    """
    Dependency that ensures user has admin role.
    
    Use this for admin-only endpoints (view all tasks, audit logs, etc.)
    
    Returns:
        User object if user is admin
        
    Raises:
        HTTPException 403: If user is not admin
        
    Usage:
        @app.get("/admin/audit-logs")
        def get_all_audit_logs(admin: User = Depends(get_current_admin_user)):
            # Only admins can access this
            return audit_logs
    """
    if current_user.role != UserRole.ADMIN:
        logger.warning(f"⚠️  Non-admin user {current_user.email} attempted admin access")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    
    logger.debug(f"✅ Admin access granted to {current_user.email}")
    return current_user

def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),  # Token optional
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Dependency for endpoints that work with or without authentication.
    
    Returns:
        User object if authenticated, None if not
        
    Does not raise exceptions - allows anonymous access.
    
    Usage:
        @app.get("/public-but-personalized")
        def endpoint(user: Optional[User] = Depends(get_optional_user)):
            if user:
                return {"message": f"Hello {user.email}"}
            return {"message": "Hello anonymous user"}
    """
    if not credentials:
        return None  # No token provided - anonymous access
    
    token = credentials.credentials
    user_id = decode_token(token)
    
    if not user_id:
        return None  # Invalid token - treat as anonymous
    
    user = db.query(User).filter(User.id == user_id).first()
    return user if user and user.is_active else None  # Return user or None