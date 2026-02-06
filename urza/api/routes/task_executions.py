"""
Task execution endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, UTC
import uuid
import logging

from urza.db.session import get_db
from urza.db import models
from urza.db.redis_client import push_task_to_queue
from urza.api import schemas
from urza.api.auth import get_current_user, check_resource_access, can_see_hidden, require_admin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/task-executions", tags=["task-executions"])


@router.post("", response_model=schemas.TaskExecutionResponse, status_code=201)
async def create_task_execution(
    execution_request: schemas.TaskExecutionCreateRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manually trigger a task execution.
    
    Creates a TaskExecution with PENDING status and pushes to Redis queue.
    
    Access rules:
    - Users can trigger their own tasks
    - Admins can trigger any task
    """
    # Get the task
    task = db.query(models.Task).filter(
        models.Task.task_id == execution_request.task_id
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Check access permissions
    check_resource_access(task.created_by_id, current_user, task.is_hidden)  # type: ignore
    
    # Check if task is active
    if task.is_active is False:
        raise HTTPException(
            status_code=400,
            detail="Cannot create execution for inactive task"
        )
    
    # Create execution
    execution_id = str(uuid.uuid4())
    execution = models.TaskExecution(
        execution_id=execution_id,
        task_id=execution_request.task_id,
        status=models.TaskStatusEnum.PENDING,
        submitted_at=datetime.now(UTC)
    )
    
    db.add(execution)
    db.flush()
    
    # Push to Redis queue
    if push_task_to_queue(execution_id):
        logger.info(f"User {current_user.username} created and queued TaskExecution {execution_id} for task {execution_request.task_id}")
    else:
        logger.error(f"Failed to queue TaskExecution {execution_id}")
        raise HTTPException(
            status_code=500,
            detail="Failed to queue task execution"
        )
    
    db.commit()
    db.refresh(execution)
    
    return schemas.TaskExecutionResponse(
        execution_id=execution.execution_id,  # type: ignore
        task_id=execution.task_id,  # type: ignore
        status=execution.status,  # type: ignore
        assigned_to=execution.assigned_to,  # type: ignore
        results=execution.results,  # type: ignore
        submitted_at=execution.submitted_at,  # type: ignore
        queued_at=execution.queued_at,  # type: ignore
        claimed_at=execution.claimed_at,  # type: ignore
        completed_at=execution.completed_at  # type: ignore
    )


@router.get("", response_model=List[schemas.TaskExecutionResponse])
async def list_task_executions(
    task_id: Optional[str] = Query(None, description="Filter by task ID"),
    status: Optional[schemas.TaskStatus] = Query(None, description="Filter by status"),
    assigned_to: Optional[str] = Query(None, description="Filter by assigned bot ID"),
    include_hidden: bool = Query(False, description="Include soft-deleted executions (admin only)"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List task executions.
    
    Access rules:
    - Users see executions for tasks they own
    - Admins see all executions
    - Admins with can_see_hidden + include_hidden=true see soft-deleted
    """
    # Build query - join with Task to check ownership
    query = db.query(models.TaskExecution).join(
        models.Task, models.TaskExecution.task_id == models.Task.task_id
    )
    
    # Apply visibility filters
    if not current_user.role.admin:
        # Non-admins see only executions for tasks they own
        query = query.filter(
            models.Task.created_by_id == current_user.user_id
        ).filter(
            models.TaskExecution.is_hidden.is_(False)
        )
    elif not include_hidden or not can_see_hidden(current_user):
        # Admins without can_see_hidden or without include_hidden flag
        query = query.filter(models.TaskExecution.is_hidden.is_(False))
    # else: admin with can_see_hidden and include_hidden=true sees all
    
    # Apply filters
    if task_id:
        query = query.filter(models.TaskExecution.task_id == task_id)
    
    if status:
        query = query.filter(models.TaskExecution.status == status.value)
    
    if assigned_to:
        query = query.filter(models.TaskExecution.assigned_to == assigned_to)
    
    executions = query.all()
    
    return [
        schemas.TaskExecutionResponse(
            execution_id=execution.execution_id,  # type: ignore
            task_id=execution.task_id,  # type: ignore
            status=execution.status,  # type: ignore
            assigned_to=execution.assigned_to,  # type: ignore
            results=execution.results,  # type: ignore
            submitted_at=execution.submitted_at,  # type: ignore
            queued_at=execution.queued_at,  # type: ignore
            claimed_at=execution.claimed_at,  # type: ignore
            completed_at=execution.completed_at  # type: ignore
        )
        for execution in executions
    ]


@router.get("/{execution_id}", response_model=schemas.TaskExecutionResponse)
async def get_task_execution(
    execution_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a single task execution by ID.
    
    Access rules:
    - Users can view executions for tasks they own
    - Admins can view any execution
    - Hidden executions only visible to users with can_see_hidden
    """
    # Join with Task to check ownership
    result = db.query(models.TaskExecution, models.Task).join(
        models.Task, models.TaskExecution.task_id == models.Task.task_id
    ).filter(models.TaskExecution.execution_id == execution_id).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="Task execution not found")
    
    execution, task = result
    
    # Check access permissions
    check_resource_access(task.created_by_id, current_user, execution.is_hidden)  # type: ignore
    
    return schemas.TaskExecutionResponse(
        execution_id=execution.execution_id,  # type: ignore
        task_id=execution.task_id,  # type: ignore
        status=execution.status,  # type: ignore
        assigned_to=execution.assigned_to,  # type: ignore
        results=execution.results,  # type: ignore
        submitted_at=execution.submitted_at,  # type: ignore
        queued_at=execution.queued_at,  # type: ignore
        claimed_at=execution.claimed_at,  # type: ignore
        completed_at=execution.completed_at  # type: ignore
    )


@router.delete("/{execution_id}", status_code=204)
async def delete_task_execution(
    execution_id: str,
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Soft delete a task execution (set is_hidden=True).
    
    Access rules:
    - Admins only
    """
    execution = db.query(models.TaskExecution).filter(
        models.TaskExecution.execution_id == execution_id
    ).first()
    
    if not execution:
        raise HTTPException(status_code=404, detail="Task execution not found")
    
    # Soft delete using update
    db.query(models.TaskExecution).filter(
        models.TaskExecution.execution_id == execution_id
    ).update({"is_hidden": True})
    db.commit()
    
    logger.info(f"Admin {current_user.username} soft-deleted TaskExecution {execution_id}")
    
    return None