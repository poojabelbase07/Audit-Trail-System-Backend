"""
Audit Log Model - Immutable record of all user actions
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.database import Base

class AuditEventType(str, enum.Enum):
    """Event types - categorizes user actions"""
    # User events
    USER_REGISTER = "USER_REGISTER"  # New user account created
    USER_LOGIN = "USER_LOGIN"  # Successful login
    USER_LOGOUT = "USER_LOGOUT"  # User logged out
    USER_LOGIN_FAILED = "USER_LOGIN_FAILED"  # Failed login attempt (wrong password)
    
    # Task events
    TASK_CREATE = "TASK_CREATE"  # New task created
    TASK_UPDATE = "TASK_UPDATE"  # Task modified (title, status, etc.)
    TASK_DELETE = "TASK_DELETE"  # Task deleted
    TASK_ASSIGN = "TASK_ASSIGN"  # Task assigned to user

class AuditLog(Base):
    """
    Audit log table - immutable record of all system actions.
    
    CRITICAL: This table is append-only - NO updates or deletes allowed.
    Ensures complete audit trail for compliance and security investigations.
    """
    __tablename__ = "audit_logs"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # When - timestamp with high precision
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)  # Indexed for time-range queries
    
    # Who - user identity
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)  # Which user performed action
    user_email = Column(String(255), nullable=False)  # Email snapshot (in case user deleted)
    user_ip = Column(INET, nullable=True)  # IP address for security tracking
    user_agent = Column(String(500), nullable=True)  # Browser/device info
    
    # What - action details
    event_type = Column(SQLEnum(AuditEventType), nullable=False, index=True)  # Type of action performed
    resource_type = Column(String(50), nullable=True)  # What was affected (e.g., "task", "user")
    resource_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # ID of affected resource
    
    # How - change details
    action = Column(String(100), nullable=False)  # Human-readable action description
    changes = Column(JSON, nullable=True)  # Before/after data for updates: {"field": {"old": X, "new": Y}}
    event_metadata = Column(JSON, nullable=True)  # Additional context (e.g., task title, error messages)
    
    # Status
    status = Column(String(50), default="success", nullable=False)  # "success" or "failure"
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")  # Link to user who performed action
    
    def __repr__(self):
        """String representation for debugging"""
        return f"<AuditLog {self.event_type} by {self.user_email} at {self.timestamp}>"
    
    # Index definitions for optimized queries
    __table_args__ = (
        # Composite index for common query pattern: "show me all actions by user X in date range Y"
        # Index order matters: most selective columns first
        # This index speeds up: WHERE user_id = X AND timestamp BETWEEN Y AND Z
    )