"""
Task Model - Represents work items in the system
"""

from sqlalchemy import Column, String, Text, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import uuid


from app.database import Base

class TaskStatus(str, enum.Enum):
    """Task status enumeration - tracks task lifecycle"""
    TODO = "todo"  # Not started
    IN_PROGRESS = "in_progress"  # Currently being worked on
    DONE = "done"  # Completed successfully
    BUG = "bug"  # Issue reported - needs fixing

class TaskPriority(str, enum.Enum):
    """Task priority enumeration - helps with work prioritization"""
    LOW = "low"  # Can be done later
    MEDIUM = "medium"  # Normal priority
    HIGH = "high"  # Urgent - should be done soon

class Task(Base):
    """
    Task table - stores work items and their metadata.
    Every task modification is logged in audit_logs table.
    """
    __tablename__ = "tasks"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Task content
    title = Column(String(200), nullable=False)  # Short description (max 200 chars)
    description = Column(Text, nullable=True)  # Detailed description (optional, unlimited length)
    
    # Task metadata
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.TODO, nullable=False, index=True)  # Current state
    priority = Column(SQLEnum(TaskPriority), default=TaskPriority.MEDIUM, nullable=False)  # Importance level
    
    # Ownership and assignment
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)  # User who created task
    assigned_to_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)  # User responsible for task
    
    # Timestamps - automatically managed
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)  # When task was created
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)  # Last modification time
    
    # Relationships - SQLAlchemy handles joins automatically
    creator = relationship("User", foreign_keys=[created_by_id], back_populates="tasks_created")  # Task creator
    assignee = relationship("User", foreign_keys=[assigned_to_id], back_populates="tasks_assigned")  # Task assignee
    
    def __repr__(self):
        """String representation for debugging"""
        return f"<Task {self.id}: {self.title} ({self.status})>"

import uuid  # Import uuid at module level for default value