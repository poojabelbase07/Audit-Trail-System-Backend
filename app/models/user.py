"""
User Model - Represents authenticated users in the system
"""

from sqlalchemy import Column, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.database import Base

class UserRole(str, enum.Enum):
    """User role enumeration - defines permission levels"""
    USER = "USER"  # Regular user - can manage own tasks
    ADMIN = "ADMIN"  # Admin user - can view all tasks and audit logs

class User(Base):
    """
    User table - stores authentication and profile information.
    All users must be authenticated to use the system.
    """
    __tablename__ = "users"
    
    # Primary key - UUID provides better security than auto-increment IDs
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Authentication fields
    email = Column(String(255), unique=True, nullable=False, index=True)  # Unique identifier for login
    password_hash = Column(String(255), nullable=False)  # bcrypt hashed password (never store plaintext)
    
    # Profile information
    full_name = Column(String(255), nullable=False)  # User's display name
    
    # Authorization
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)  # Permission level
    
    # Account status
    is_active = Column(Boolean, default=True, nullable=False)  # Soft delete - deactivate instead of deleting
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)  # Account creation time
    last_login = Column(DateTime, nullable=True)  # Last successful login (updated on each login)
    
    # Relationships - SQLAlchemy handles foreign key queries
    tasks_created = relationship("Task", foreign_keys="Task.created_by_id", back_populates="creator")  # Tasks this user created
    tasks_assigned = relationship("Task", foreign_keys="Task.assigned_to_id", back_populates="assignee")  # Tasks assigned to this user
    audit_logs = relationship("AuditLog", back_populates="user")  # All audit logs for this user
    
    def __repr__(self):
        """String representation for debugging"""
        return f"<User {self.email} ({self.role})>"