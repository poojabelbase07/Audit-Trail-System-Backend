"""
Audit Log Schemas - Pydantic models for audit log responses
"""

from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime
from uuid import UUID

from app.models.audit_log import AuditEventType

class AuditLogResponse(BaseModel):
    """Schema for audit log entries in responses"""
    id: UUID  # Log entry unique identifier
    timestamp: datetime  # When action occurred
    user_id: UUID  # User who performed action
    user_email: str  # User email (snapshot)
    user_ip: Optional[str]  # IP address of request
    user_agent: Optional[str]  # Browser/device info
    event_type: AuditEventType  # Type of action
    resource_type: Optional[str]  # What was affected
    resource_id: Optional[UUID]  # ID of affected resource
    action: str  # Human-readable description
    changes: Optional[dict[str, Any]]  # Before/after data
    metadata: Optional[dict[str, Any]]  # Additional context
    status: str  # "success" or "failure"
    
    class Config:
        orm_mode = True  # Allow creation from SQLAlchemy models

class AuditLogListResponse(BaseModel):
    """Schema for paginated audit log list"""
    logs: list[AuditLogResponse]  # List of audit logs
    total: int  # Total count
    page: int  # Current page
    page_size: int  # Items per page

class AuditLogFilters(BaseModel):
    """Schema for audit log query filters"""
    user_id: Optional[UUID] = None  # Filter by user
    event_type: Optional[AuditEventType] = None  # Filter by event type
    start_date: Optional[datetime] = None  # Filter by date range (start)
    end_date: Optional[datetime] = None  # Filter by date range (end)
    resource_type: Optional[str] = None  # Filter by resource type
    resource_id: Optional[UUID] = None  # Filter by specific resource

class AuditStatsResponse(BaseModel):
    """Schema for audit log statistics"""
    total_events: int  # Total audit log entries
    events_today: int  # Events in last 24 hours
    failed_logins: int  # Failed login attempts
    total_users: int  # Unique users with activity
    total_tasks_created: int  # Tasks created count
    total_tasks_updated: int  # Tasks updated count
    total_tasks_deleted: int  # Tasks deleted count