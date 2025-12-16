"""
Audit Logger Utility - Automatically creates audit log entries
"""

from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from fastapi import Request
import logging

from app.models import AuditLog, User, AuditEventType

logger = logging.getLogger(__name__)

def create_audit_log(
    db: Session,
    user: User,
    event_type: AuditEventType,
    action: str,
    request: Optional[Request] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    changes: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    status: str = "success"
) -> AuditLog:
    """
    Create audit log entry for user action.
    
    Args:
        db: Database session
        user: User who performed action
        event_type: Type of event (from AuditEventType enum)
        action: Human-readable description
        request: FastAPI request object (for IP and user agent)
        resource_type: What was affected (e.g., "task", "user")
        resource_id: ID of affected resource
        changes: Before/after data for updates
        metadata: Additional context
        status: "success" or "failure"
        
    Returns:
        Created AuditLog object
        
    Example:
        create_audit_log(
            db=db,
            user=current_user,
            event_type=AuditEventType.TASK_CREATE,
            action="Created task 'Fix homepage bug'",
            request=request,
            resource_type="task",
            resource_id=str(task.id),
            metadata={"task_title": task.title}
        )
    """
    
    # Extract IP address from request
    user_ip = None
    if request:
        # Check X-Forwarded-For header first (for proxies/load balancers)
        user_ip = request.headers.get("X-Forwarded-For")
        if user_ip:
            user_ip = user_ip.split(",")[0].strip()  # Take first IP if multiple
        else:
            user_ip = request.client.host  # Fallback to direct connection IP
    
    # Extract user agent from request
    user_agent = None
    if request:
        user_agent = request.headers.get("User-Agent")
    
    # Create audit log entry
    audit_log = AuditLog(
        user_id=user.id,  # Who performed action
        user_email=user.email,  # Email snapshot (in case user deleted)
        user_ip=user_ip,  # IP address
        user_agent=user_agent,  # Browser/device info
        event_type=event_type,  # Event category
        resource_type=resource_type,  # What was affected
        resource_id=resource_id,  # ID of affected resource
        action=action,  # Human-readable description
        changes=changes,  # Before/after data
        metadata=metadata,  # Additional context
        status=status,  # Success or failure
    )
    
    # Save to database
    try:
        db.add(audit_log)  # Add to session
        db.commit()  # Commit transaction
        db.refresh(audit_log)  # Refresh to get generated ID and timestamp
        logger.info(f"✅ Audit log created: {event_type.value} by {user.email}")
        return audit_log
    except Exception as e:
        db.rollback()  # Rollback on error
        logger.error(f"❌ Failed to create audit log: {str(e)}", exc_info=True)
        raise  # Re-raise to let caller handle error

def log_task_create(db: Session, user: User, task: Any, request: Request) -> None:
    """Helper function to log task creation"""
    create_audit_log(
        db=db,
        user=user,
        event_type=AuditEventType.TASK_CREATE,
        action=f"Created task '{task.title}'",
        request=request,
        resource_type="task",
        resource_id=str(task.id),
        metadata={
            "task_title": task.title,
            "task_status": task.status.value,
            "task_priority": task.priority.value,
        }
    )

def log_task_update(
    db: Session,
    user: User,
    task: Any,
    old_data: Dict[str, Any],
    new_data: Dict[str, Any],
    request: Request
) -> None:
    """Helper function to log task updates with before/after data"""
    
    # Build changes dictionary
    changes = {}
    for field, new_value in new_data.items():
        old_value = old_data.get(field)
        if old_value != new_value:  # Only log actual changes
            changes[field] = {"old": old_value, "new": new_value}
    
    # Create readable action description
    changed_fields = ", ".join(changes.keys())
    action = f"Updated task '{task.title}' ({changed_fields})"
    
    create_audit_log(
        db=db,
        user=user,
        event_type=AuditEventType.TASK_UPDATE,
        action=action,
        request=request,
        resource_type="task",
        resource_id=str(task.id),
        changes=changes,
        metadata={"task_title": task.title}
    )

def log_task_delete(db: Session, user: User, task: Any, request: Request) -> None:
    """Helper function to log task deletion"""
    create_audit_log(
        db=db,
        user=user,
        event_type=AuditEventType.TASK_DELETE,
        action=f"Deleted task '{task.title}'",
        request=request,
        resource_type="task",
        resource_id=str(task.id),
        metadata={
            "task_title": task.title,
            "task_status": task.status.value,
        }
    )

def log_user_login(db: Session, user: User, request: Request, success: bool = True) -> None:
    """Helper function to log login attempts"""
    event_type = AuditEventType.USER_LOGIN if success else AuditEventType.USER_LOGIN_FAILED
    action = "Successful login" if success else "Failed login attempt"
    status = "success" if success else "failure"
    
    create_audit_log(
        db=db,
        user=user,
        event_type=event_type,
        action=action,
        request=request,
        status=status
    )

def log_user_logout(db: Session, user: User, request: Request) -> None:
    """Helper function to log user logout"""
    create_audit_log(
        db=db,
        user=user,
        event_type=AuditEventType.USER_LOGOUT,
        action="User logged out",
        request=request
    )

def log_user_register(db: Session, user: User, request: Request) -> None:
    """Helper function to log user registration"""
    create_audit_log(
        db=db,
        user=user,
        event_type=AuditEventType.USER_REGISTER,
        action=f"New user registered: {user.email}",
        request=request,
        resource_type="user",
        resource_id=str(user.id)
    )