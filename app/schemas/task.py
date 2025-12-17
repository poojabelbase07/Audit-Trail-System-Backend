"""
Task Schemas - Pydantic models for task operations
"""

from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID

from app.models.task import TaskStatus, TaskPriority

# DO NOT import from app.schemas here - causes circular import

class TaskBase(BaseModel):
    """Base schema with common task fields"""
    title: str  # Task title/summary
    description: Optional[str] = None  # Detailed description (optional)
    priority: TaskPriority = TaskPriority.MEDIUM  # Default to medium priority
    assigned_to_id: Optional[UUID] = None  # User to assign task to (optional)

class TaskCreate(TaskBase):
    """Schema for creating new task"""
    
    @validator('title')
    def validate_title(cls, v):
        """Ensure title is not empty and within length limits"""
        if not v or not v.strip():  # Empty title check
            raise ValueError('Task title cannot be empty')
        if len(v.strip()) < 3:  # Minimum length
            raise ValueError('Task title must be at least 3 characters')
        if len(v.strip()) > 200:  # Maximum length (database constraint)
            raise ValueError('Task title cannot exceed 200 characters')
        return v.strip()  # Return trimmed title
    
    @validator('description')
    def validate_description(cls, v):
        """Validate description length if provided"""
        if v is not None and len(v) > 5000:  # Maximum length check
            raise ValueError('Task description cannot exceed 5000 characters')
        return v.strip() if v else None  # Trim whitespace

class TaskUpdate(BaseModel):
    """Schema for updating existing task - all fields optional"""
    title: Optional[str] = None  # Update title if provided
    description: Optional[str] = None  # Update description if provided
    status: Optional[TaskStatus] = None  # Update status if provided
    priority: Optional[TaskPriority] = None  # Update priority if provided
    assigned_to_id: Optional[UUID] = None  # Reassign task if provided
    
    @validator('title')
    def validate_title(cls, v):
        """Same validation as TaskCreate"""
        if v is not None:  # Only validate if provided
            if not v or not v.strip():
                raise ValueError('Task title cannot be empty')
            if len(v.strip()) < 3:
                raise ValueError('Task title must be at least 3 characters')
            if len(v.strip()) > 200:
                raise ValueError('Task title cannot exceed 200 characters')
            return v.strip()
        return v
    
    @validator('description')
    def validate_description(cls, v):
        """Same validation as TaskCreate"""
        if v is not None and len(v) > 5000:
            raise ValueError('Task description cannot exceed 5000 characters')
        return v.strip() if v else None

class TaskResponse(TaskBase):
    """Schema for task data in responses"""
    id: UUID  # Task unique identifier
    status: TaskStatus  # Current status
    created_by_id: UUID  # User who created task
    created_at: datetime  # Creation timestamp
    updated_at: datetime  # Last modification timestamp
    
    class Config:
        from_attributes = True  # Pydantic V2 - replaces orm_mode

class TaskListResponse(BaseModel):
    """Schema for paginated task list"""
    tasks: List[TaskResponse]  # List of tasks (using List from typing)
    total: int  # Total count (for pagination)
    page: int  # Current page number
    page_size: int  # Items per page