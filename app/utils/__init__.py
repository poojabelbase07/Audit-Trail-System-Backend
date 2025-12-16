"""
Utilities Package - Helper functions and tools

This package contains:
- audit_logger.py: Automatic audit log creation helpers
"""

from app.utils.audit_logger import (
    create_audit_log,
    log_task_create,
    log_task_update,
    log_task_delete,
    log_user_login,
    log_user_logout,
    log_user_register,
)

# Export audit logging functions
__all__ = [
    "create_audit_log",
    "log_task_create",
    "log_task_update",
    "log_task_delete",
    "log_user_login",
    "log_user_logout",
    "log_user_register",
]