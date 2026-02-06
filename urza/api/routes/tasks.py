"""
Task management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, UTC
import uuid
import logging
from croniter import croniter

from urza.db.session import get_db
from urza.db import models
from urza.db.redis_client import push_task_to_queue
from urza.api.schemas import schemas
from urza.api.auth import get_current_user, check_resource_access, can_see_hidden

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tasks", tags=["tasks"])


def calculate_next_run(cron_schedule: str, base_time: Optional[datetime] = None) -> datetime:
    """Calculate next run time from cron schedule"""
    if base_time is None:
        base_time = datetime.now(UTC)
    
    try:
        cron = croniter(cron_schedule, base_time)
        return cron.get_next(datetime)
    except Exception as e:
        logger.error(f"Invalid cron schedule '{cron_schedule}': {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid cron schedule: {str(e)}"
        )


@router.post("", response_model=schemas.TaskResponse, status_code=201)
async def create_task(
    task_request: schemas.TaskCreateRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new task.
    
    - If run_now=True: sets next_run to now and creates TaskExecution with PENDING status
    - If cron_schedule provided: calculates next_run from cron
    - Otherwise: next_run remains None (manual execution only)
    """
    task_id = str(uuid.uuid4())
    
    # Calculate next_run
    next_run = None
    if task_request.run_now:
        next_run = datetime.now(UTC)
    elif task_request.cron_schedule:
        next_run = calculate_next_run(task_request.cron_schedule)
    
    # Create task
    task = models.Task(
        task_id=task_id,
        name=task_request.name,
        description=task_request.description,
        config=task_request.config,
        created_by_id=current_user.user_id,
        timeout_seconds=task_request.timeout_seconds,
        cron_schedule=task_request.cron_schedule,
        next_run=next_run,
        is_active=True,
        is_hidden=False
    )
    
    db.add(task)
    
    # If run_now, create TaskExecution with PENDING status
    if task_request.run_now:
        execution_id = str(uuid.uuid4())
        execution = models.TaskExecution(
            execution_id=execution_id,
            task_id=task_id,
            created_by_id=current_user.user_id,
            status=models.TaskStatusEnum.PENDING,
            submitted_at=datetime.now(UTC)
        )
        db.add(execution)
        db.flush()  # Ensure execution is in DB before pushing to Redis
        
        # Push to Redis queue for publisher to pick up
        if push_task_to_queue(execution_id):
            logger.info(f"Created and queued TaskExecution {execution_id} for task {task_id}")
        else:
            logger.error(f"Failed to queue TaskExecution {execution_id} - publisher may not pick it up")
    
    db.commit()
    db.refresh(task)
    
    logger.info(f"User {current_user.username} created task {task_id}")
    
    return schemas.TaskResponse(
        task_id=task.task_id,
        name=task.name,
        description=task.description,
        created_at=task.created_at,
        next_run=task.next_run,
        last_run=task.last_run,
        created_by_username=current_user.username,
        config=task.config,
        cron_schedule=task.cron_schedule,
        timeout_seconds=task.timeout_seconds,
        is_active=task.is_active
    )


@router.get("", response_model=List[schemas.TaskResponse])
async def list_tasks(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    include_hidden: bool = Query(False, description="Include soft-deleted tasks (admin only)"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List tasks.
    
    Access rules:
    - Non-admins: only their own non-hidden tasks
    - Admins: all non-hidden tasks
    - Admins with can_see_hidden + include_hidden=true: all tasks
    """
    query = db.query(models.Task, models.User).join(
        models.User, models.Task.created_by_id == models.User.user_id
    )
    
    # Apply visibility filters
    if not current_user.role.admin:
        # Non-admins see only their own non-hidden tasks
        query = query.filter(
            models.Task.created_by_id == current_user.user_id,
            models.Task.is_hidden == False
        )
    elif not include_hidden or not can_see_hidden(current_user):
        # Admins without can_see_hidden or without include_hidden flag
        query = query.filter(models.Task.is_hidden == False)
    # else: admin with can_see_hidden and include_hidden=true sees all
    
    # Apply active filter if provided
    if is_active is not None:
        query = query.filter(models.Task.is_active == is_active)
    
    results = query.all()
    
    return [
        schemas.TaskResponse(
            task_id=task.task_id,
            name=task.name,
            description=task.description,
            created_at=task.created_at,
            next_run=task.next_run,
            last_run=task.last_run,
            created_by_username=user.username,
            config=task.config,
            cron_schedule=task.cron_schedule,
            timeout_seconds=task.timeout_seconds,
            is_active=task.is_active
        )
        for task, user in results
    ]


@router.get("/{task_id}", response_model=schemas.TaskResponse)
async def get_task(
    task_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a single task by ID.
    
    Access rules:
    - Users can get their own tasks
    - Admins can get any task
    - Hidden tasks only visible to users with can_see_hidden
    """
    result = db.query(models.Task, models.User).join(
        models.User, models.Task.created_by_id == models.User.user_id
    ).filter(models.Task.task_id == task_id).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task, user = result
    
    # Check access permissions
    check_resource_access(task.created_by_id, current_user, task.is_hidden)
    
    return schemas.TaskResponse(
        task_id=task.task_id,
        name=task.name,
        description=task.description,
        created_at=task.created_at,
        next_run=task.next_run,
        last_run=task.last_run,
        created_by_username=user.username,
        config=task.config,
        cron_schedule=task.cron_schedule,
        timeout_seconds=task.timeout_seconds,
        is_active=task.is_active
    )


@router.put("/{task_id}", response_model=schemas.TaskResponse)
async def update_task(
    task_id: str,
    task_update: schemas.TaskUpdateRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a task.
    
    Access rules:
    - Users can update their own tasks
    - Admins can update any task
    
    Updatable fields: name, description, config, cron_schedule, timeout_seconds, is_active
    If cron_schedule is updated, next_run is recalculated
    """
    result = db.query(models.Task, models.User).join(
        models.User, models.Task.created_by_id == models.User.user_id
    ).filter(models.Task.task_id == task_id).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task, user = result
    
    # Check access permissions
    check_resource_access(task.created_by_id, current_user, task.is_hidden)
    
    # Update fields if provided
    update_data = task_update.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(task, field, value)
    
    # Recalculate next_run if cron_schedule was updated
    if "cron_schedule" in update_data and task.cron_schedule:
        task.next_run = calculate_next_run(task.cron_schedule)
        logger.info(f"Recalculated next_run for task {task_id}: {task.next_run}")
    
    db.commit()
    db.refresh(task)
    
    logger.info(f"User {current_user.username} updated task {task_id}")
    
    return schemas.TaskResponse(
        task_id=task.task_id,
        name=task.name,
        description=task.description,
        created_at=task.created_at,
        next_run=task.next_run,
        last_run=task.last_run,
        created_by_username=user.username,
        config=task.config,
        cron_schedule=task.cron_schedule,
        timeout_seconds=task.timeout_seconds,
        is_active=task.is_active
    )


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Soft delete a task (set is_hidden=True).
    
    Access rules:
    - Users can delete their own tasks
    - Admins can delete any task
    """
    task = db.query(models.Task).filter_by(task_id=task_id).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Check access permissions
    check_resource_access(task.created_by_id, current_user, task.is_hidden)
    
    # Soft delete
    task.is_hidden = True
    db.commit()
    
    logger.info(f"User {current_user.username} soft-deleted task {task_id}")
    
    return None