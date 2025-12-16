"""
Models Package - Exports all database models for easy importing
"""

# Import all models to register them with SQLAlchemy Base
# This ensures create_all() knows about all tables
from app.models.user import User, UserRole
from app.models.task import Task, TaskStatus, TaskPriority
from app.models.audit_log import AuditLog, AuditEventType

# Export models for convenient importing
# Usage: from app.models import User, Task, AuditLog
__all__ = [
    "User",
    "UserRole",
    "Task", 
    "TaskStatus",
    "TaskPriority",
    "AuditLog",
    "AuditEventType",
]