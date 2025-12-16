"""
Audit Logs API - View audit trail and statistics
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import Optional
from datetime import datetime, timedelta
from uuid import UUID
import logging

from app.database import get_db
from app.schemas import AuditLogResponse, AuditLogListResponse, AuditStatsResponse
from app.models import AuditLog, User, AuditEventType, Task
from app.core.dependencies import get_current_user, get_current_admin_user

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/logs", response_model=AuditLogListResponse)
def get_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    user_id: Optional[UUID] = Query(None, description="Filter by user ID"),
    event_type: Optional[AuditEventType] = Query(None, description="Filter by event type"),
    start_date: Optional[datetime] = Query(None, description="Filter from date"),
    end_date: Optional[datetime] = Query(None, description="Filter to date"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get paginated audit logs.
    
    Regular users see only their own actions.
    Admins see all actions or filtered by user_id.
    
    Query parameters:
        - page: Page number
        - page_size: Items per page (max 100)
        - user_id: Filter by specific user (admin only)
        - event_type: Filter by event type
        - start_date: Filter from timestamp
        - end_date: Filter to timestamp
        
    Returns:
        AuditLogListResponse with logs and pagination
    """
    logger.info(f"➡️  Get audit logs request from: {current_user.email}")
    
    # Build base query
    query = db.query(AuditLog)
    
    # Regular users can only see their own logs
    if current_user.role.value != "ADMIN":
        query = query.filter(AuditLog.user_id == current_user.id)
        if user_id and user_id != current_user.id:
            # Regular user trying to filter by different user
            logger.warning(f"⚠️  User {current_user.email} attempted to view other user's logs")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own audit logs"
            )
    else:
        # Admin can filter by specific user
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
    
    # Apply filters
    if event_type:
        query = query.filter(AuditLog.event_type == event_type)
    if start_date:
        query = query.filter(AuditLog.timestamp >= start_date)
    if end_date:
        query = query.filter(AuditLog.timestamp <= end_date)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * page_size
    logs = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(page_size).all()
    
    logger.info(f"✅ Returning {len(logs)} audit logs (total: {total})")
    
    return AuditLogListResponse(
        logs=[AuditLogResponse.from_orm(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size
    )

@router.get("/logs/{log_id}", response_model=AuditLogResponse)
def get_audit_log(
    log_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get single audit log entry by ID.
    
    Regular users can only access their own logs.
    Admins can access any log.
    
    Returns:
        AuditLogResponse
        
    Raises:
        404: Log not found
        403: No permission
    """
    logger.info(f"➡️  Get audit log {log_id} request from: {current_user.email}")
    
    # Find log
    log = db.query(AuditLog).filter(AuditLog.id == log_id).first()
    if not log:
        logger.warning(f"⚠️  Audit log {log_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit log with ID {log_id} not found"
        )
    
    # Check permissions
    if current_user.role.value != "ADMIN" and log.user_id != current_user.id:
        logger.warning(f"⚠️  User {current_user.email} denied access to log {log_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own audit logs"
        )
    
    logger.info(f"✅ Returning audit log {log_id}")
    return AuditLogResponse.from_orm(log)

@router.get("/stats", response_model=AuditStatsResponse)
def get_audit_stats(
    current_admin: User = Depends(get_current_admin_user),  # Admin only
    db: Session = Depends(get_db)
):
    """
    Get audit log statistics (admin only).
    
    Returns:
        AuditStatsResponse with aggregated metrics
    """
    logger.info(f"➡️  Get audit stats request from: {current_admin.email}")
    
    # Total events
    total_events = db.query(func.count(AuditLog.id)).scalar()
    
    # Events today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    events_today = db.query(func.count(AuditLog.id)).filter(
        AuditLog.timestamp >= today_start
    ).scalar()
    
    # Failed logins
    failed_logins = db.query(func.count(AuditLog.id)).filter(
        AuditLog.event_type == AuditEventType.USER_LOGIN_FAILED
    ).scalar()
    
    # Total users with activity
    total_users = db.query(func.count(func.distinct(AuditLog.user_id))).scalar()
    
    # Task statistics
    total_tasks_created = db.query(func.count(AuditLog.id)).filter(
        AuditLog.event_type == AuditEventType.TASK_CREATE
    ).scalar()
    
    total_tasks_updated = db.query(func.count(AuditLog.id)).filter(
        AuditLog.event_type == AuditEventType.TASK_UPDATE
    ).scalar()
    
    total_tasks_deleted = db.query(func.count(AuditLog.id)).filter(
        AuditLog.event_type == AuditEventType.TASK_DELETE
    ).scalar()
    
    logger.info(f"✅ Returning audit statistics")
    
    return AuditStatsResponse(
        total_events=total_events or 0,
        events_today=events_today or 0,
        failed_logins=failed_logins or 0,
        total_users=total_users or 0,
        total_tasks_created=total_tasks_created or 0,
        total_tasks_updated=total_tasks_updated or 0,
        total_tasks_deleted=total_tasks_deleted or 0
    )

@router.get("/my-history", response_model=AuditLogListResponse)
def get_my_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    event_type: Optional[AuditEventType] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's audit history.
    
    Convenience endpoint for users to view their own activity.
    Same as /logs but automatically filtered to current user.
    
    Returns:
        AuditLogListResponse with user's activity
    """
    logger.info(f"➡️  Get my history request from: {current_user.email}")
    
    # Query only current user's logs
    query = db.query(AuditLog).filter(AuditLog.user_id == current_user.id)
    
    # Apply filters
    if event_type:
        query = query.filter(AuditLog.event_type == event_type)
    if start_date:
        query = query.filter(AuditLog.timestamp >= start_date)
    if end_date:
        query = query.filter(AuditLog.timestamp <= end_date)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * page_size
    logs = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(page_size).all()
    
    logger.info(f"✅ Returning {len(logs)} history entries")
    
    return AuditLogListResponse(
        logs=[AuditLogResponse.from_orm(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size
    )