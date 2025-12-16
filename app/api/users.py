"""
Users API - User management endpoints (admin only)
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
import logging

from app.database import get_db
from app.schemas import UserResponse
from app.models import User
from app.core.dependencies import get_current_admin_user

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("", response_model=list[UserResponse])
def get_all_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_admin: User = Depends(get_current_admin_user),  # Admin only
    db: Session = Depends(get_db)
):
    """
    Get all users (admin only).
    
    Query parameters:
        - page: Page number
        - page_size: Items per page (max 100)
        - is_active: Filter by active status
        
    Returns:
        List of UserResponse
    """
    logger.info(f"➡️  Get all users request from admin: {current_admin.email}")
    
    # Build query
    query = db.query(User)
    
    # Apply filter
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    # Get total
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * page_size
    users = query.order_by(User.created_at.desc()).offset(offset).limit(page_size).all()
    
    logger.info(f"✅ Returning {len(users)} users (total: {total})")
    
    return [UserResponse.from_orm(user) for user in users]

@router.get("/{user_id}", response_model=UserResponse)
def get_user_by_id(
    user_id: UUID,
    current_admin: User = Depends(get_current_admin_user),  # Admin only
    db: Session = Depends(get_db)
):
    """
    Get user by ID (admin only).
    
    Returns:
        UserResponse
        
    Raises:
        404: User not found
    """
    logger.info(f"➡️  Get user {user_id} request from admin: {current_admin.email}")
    
    # Find user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.warning(f"⚠️  User {user_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    logger.info(f"✅ Returning user {user_id}")
    return UserResponse.from_orm(user)

@router.patch("/{user_id}/deactivate", response_model=UserResponse)
def deactivate_user(
    user_id: UUID,
    current_admin: User = Depends(get_current_admin_user),  # Admin only
    db: Session = Depends(get_db)
):
    """
    Deactivate user account (admin only).
    
    Soft delete - sets is_active to False instead of deleting record.
    Preserves audit trail.
    
    Returns:
        Updated UserResponse
        
    Raises:
        404: User not found
        400: Cannot deactivate admin
    """
    logger.info(f"➡️  Deactivate user {user_id} request from admin: {current_admin.email}")
    
    # Find user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.warning(f"⚠️  User {user_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    # Cannot deactivate admin users
    if user.role.value == "ADMIN":
        logger.warning(f"⚠️  Attempted to deactivate admin user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate admin users"
        )
    
    # Deactivate
    user.is_active = False
    
    try:
        db.commit()
        db.refresh(user)
        logger.info(f"✅ User {user_id} deactivated")
        return UserResponse.from_orm(user)
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to deactivate user: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate user"
        )

@router.patch("/{user_id}/activate", response_model=UserResponse)
def activate_user(
    user_id: UUID,
    current_admin: User = Depends(get_current_admin_user),  # Admin only
    db: Session = Depends(get_db)
):
    """
    Activate user account (admin only).
    
    Re-enables deactivated account.
    
    Returns:
        Updated UserResponse
        
    Raises:
        404: User not found
    """
    logger.info(f"➡️  Activate user {user_id} request from admin: {current_admin.email}")
    
    # Find user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.warning(f"⚠️  User {user_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    # Activate
    user.is_active = True
    
    try:
        db.commit()
        db.refresh(user)
        logger.info(f"✅ User {user_id} activated")
        return UserResponse.from_orm(user)
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to activate user: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to activate user"
        )