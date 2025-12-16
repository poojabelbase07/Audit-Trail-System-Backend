"""
Tasks API - CRUD operations for task management
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
import logging

from app.database import get_db
from app.schemas import TaskCreate, TaskUpdate, TaskResponse, TaskListResponse
from app.models import Task, User, TaskStatus, TaskPriority
from app.core.dependencies import get_current_user, get_current_admin_user
from app.utils.audit_logger import log_task_create, log_task_update, log_task_delete

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("", response_model=TaskListResponse)
def get_tasks(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),  # Minimum 1
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),  # Between 1-100
    status: Optional[TaskStatus] = Query(None, description="Filter by status"),
    priority: Optional[TaskPriority] = Query(None, description="Filter by priority"),
    current_user: User = Depends(get_current_user),  # Require authentication
    db: Session = Depends(get_db)
):
    """
    Get paginated list of tasks.
    
    Regular users see only their tasks (created by or assigned to them).
    Admins see all tasks.
    
    Query parameters:
        - page: Page number (default 1)
        - page_size: Items per page (default 20, max 100)
        - status: Filter by task status
        - priority: Filter by task priority
        
    Returns:
        TaskListResponse with tasks, pagination info
    """
    logger.info(f"➡️  Get tasks request from: {current_user.email} (page {page})")
    
    # Build base query
    query = db.query(Task)
    
    # Filter tasks based on user role
    if current_user.role.value != "ADMIN":  # Regular user
        # Show only tasks created by or assigned to this user
        query = query.filter(
            (Task.created_by_id == current_user.id) | (Task.assigned_to_id == current_user.id)
        )
    # Admins see all tasks (no filter)
    
    # Apply optional filters
    if status:
        query = query.filter(Task.status == status)
    if priority:
        query = query.filter(Task.priority == priority)
    
    # Get total count (before pagination)
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * page_size
    tasks = query.order_by(Task.created_at.desc()).offset(offset).limit(page_size).all()
    
    logger.info(f"✅ Returning {len(tasks)} tasks (total: {total})")
    
    return TaskListResponse(
        tasks=[TaskResponse.from_orm(task) for task in tasks],
        total=total,
        page=page,
        page_size=page_size
    )

@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get single task by ID.
    
    Regular users can only access their own tasks.
    Admins can access any task.
    
    Returns:
        TaskResponse
        
    Raises:
        404: Task not found
        403: No permission to access task
    """
    logger.info(f"➡️  Get task {task_id} request from: {current_user.email}")
    
    # Find task
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        logger.warning(f"⚠️  Task {task_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found"
        )
    
    # Check permissions (regular users can only access their tasks)
    if current_user.role.value != "ADMIN":
        if task.created_by_id != current_user.id and task.assigned_to_id != current_user.id:
            logger.warning(f"⚠️  User {current_user.email} denied access to task {task_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this task"
            )
    
    logger.info(f"✅ Returning task {task_id}")
    return TaskResponse.from_orm(task)

@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    task_data: TaskCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create new task.
    
    Process:
        1. Validate input (Pydantic)
        2. Verify assigned_to user exists (if provided)
        3. Create task
        4. Log creation in audit trail
        
    Returns:
        Created task
        
    Raises:
        404: Assigned user not found
        500: Database error
    """
    logger.info(f"➡️  Create task request from: {current_user.email}")
    
    # Verify assigned_to user exists
    if task_data.assigned_to_id:
        assigned_user = db.query(User).filter(User.id == task_data.assigned_to_id).first()
        if not assigned_user:
            logger.warning(f"⚠️  Assigned user {task_data.assigned_to_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {task_data.assigned_to_id} not found"
            )
    
    # Create task
    new_task = Task(
        title=task_data.title,
        description=task_data.description,
        priority=task_data.priority,
        assigned_to_id=task_data.assigned_to_id,
        created_by_id=current_user.id,
        # status defaults to TODO
    )
    
    try:
        db.add(new_task)
        db.commit()
        db.refresh(new_task)
        logger.info(f"✅ Task created: {new_task.id} - {new_task.title}")
        
        # Log creation in audit trail
        log_task_create(db=db, user=current_user, task=new_task, request=request)
        
        return TaskResponse.from_orm(new_task)
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Task creation failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create task. Please try again later."
        )

@router.put("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: UUID,
    task_data: TaskUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update existing task.
    
    Regular users can only update their own tasks.
    Admins can update any task.
    
    Process:
        1. Find task
        2. Check permissions
        3. Capture old data
        4. Update task
        5. Log changes in audit trail
        
    Returns:
        Updated task
        
    Raises:
        404: Task not found
        403: No permission
        500: Database error
    """
    logger.info(f"➡️  Update task {task_id} request from: {current_user.email}")
    
    # Find task
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        logger.warning(f"⚠️  Task {task_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found"
        )
    
    # Check permissions
    if current_user.role.value != "ADMIN":
        if task.created_by_id != current_user.id and task.assigned_to_id != current_user.id:
            logger.warning(f"⚠️  User {current_user.email} denied access to update task {task_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this task"
            )
    
    # Capture old data for audit log
    old_data = {
        "title": task.title,
        "description": task.description,
        "status": task.status.value,
        "priority": task.priority.value,
        "assigned_to_id": str(task.assigned_to_id) if task.assigned_to_id else None
    }
    
    # Update fields (only if provided)
    if task_data.title is not None:
        task.title = task_data.title
    if task_data.description is not None:
        task.description = task_data.description
    if task_data.status is not None:
        task.status = task_data.status
    if task_data.priority is not None:
        task.priority = task_data.priority
    if task_data.assigned_to_id is not None:
        # Verify new assigned user exists
        if task_data.assigned_to_id:
            assigned_user = db.query(User).filter(User.id == task_data.assigned_to_id).first()
            if not assigned_user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"User with ID {task_data.assigned_to_id} not found"
                )
        task.assigned_to_id = task_data.assigned_to_id
    
    # Capture new data
    new_data = {
        "title": task.title,
        "description": task.description,
        "status": task.status.value,
        "priority": task.priority.value,
        "assigned_to_id": str(task.assigned_to_id) if task.assigned_to_id else None
    }
    
    try:
        db.commit()
        db.refresh(task)
        logger.info(f"✅ Task updated: {task_id}")
        
        # Log update in audit trail
        log_task_update(
            db=db,
            user=current_user,
            task=task,
            old_data=old_data,
            new_data=new_data,
            request=request
        )
        
        return TaskResponse.from_orm(task)
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Task update failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update task. Please try again later."
        )

@router.delete("/{task_id}", status_code=status.HTTP_200_OK)
def delete_task(
    task_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete task.
    
    Regular users can only delete their own tasks.
    Admins can delete any task.
    
    Returns:
        Success message
        
    Raises:
        404: Task not found
        403: No permission
        500: Database error
    """
    logger.info(f"➡️  Delete task {task_id} request from: {current_user.email}")
    
    # Find task
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        logger.warning(f"⚠️  Task {task_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found"
        )
    
    # Check permissions
    if current_user.role.value != "ADMIN":
        if task.created_by_id != current_user.id:
            logger.warning(f"⚠️  User {current_user.email} denied access to delete task {task_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete tasks you created"
            )
    
    try:
        # Log deletion before removing (need task data for log)
        log_task_delete(db=db, user=current_user, task=task, request=request)
        
        # Delete task
        db.delete(task)
        db.commit()
        logger.info(f"✅ Task deleted: {task_id}")
        
        return {"message": "Task deleted successfully"}
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Task deletion failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete task. Please try again later."
        )