"""
Tasks endpoint - manage task definitions and execution
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from urza.db.session import get_db
from urza.api import schemas
from urza.db import models
from urza.api.auth import (
    get_current_user,
    require_admin,
    can_see_hidden
)
from typing import List, Optional
import uuid
from datetime import datetime, UTC
from croniter import croniter

router = APIRouter(prefix="/tasks", tags=["tasks"])

def calculate_next_run(cron_schedule: str, base_time: datetime = None) -> datetime:
    """Calculate next run time from cron schedule"""
    if not base_time:
        base_time = datetime.now(UTC)
    
    try:
        cron = croniter(cron_schedule, base_time)
        return cron.get_next(datetime)
    except Exception as e:
        raise ValueError(f"Invalid cron schedule: {e}")

@router.post("/", response_model=schemas.TaskResponse, status_code=201)
async def create_task(
    name: str,
    config: dict,
    capability_id: str,
    platform_id: str,
    timeout_seconds: int = 3600,
    description: Optional[str] = None,
    cron_schedule: Optional[str] = None,
    notification_config_id: Optional[str] = None,
    proof_of_work_required: bool = False,
    run_now: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Create a new task.
    
    - If cron_schedule is provided: scheduled task (runs on cron)
    - If run_now=True: creates immediate TaskExecution
    - If neither: error (task must either run now or be scheduled)
    
    All authenticated users can create tasks.
    """
    # Validate: must have cron OR run_now
    if not cron_schedule and not run_now:
        raise HTTPException(
            status_code=400,
            detail="Task must either have a cron_schedule or run_now=True"
        )
    
    # Validate cron schedule if provided
    if cron_schedule:
        try:
            calculate_next_run(cron_schedule)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    # Verify capability exists
    capability = db.query(models.Capability).filter(
        models.Capability.id == capability_id
    ).first()
    if not capability:
        raise HTTPException(status_code=404, detail="Capability not found")
    
    # Verify platform exists
    platform = db.query(models.Platform).filter(
        models.Platform.id == platform_id
    ).first()
    if not platform:
        raise HTTPException(status_code=404, detail="Platform not found")
    
    # Note: We're NOT validating notification_config_id (mocked for now)
    
    # Calculate next_run if cron schedule provided
    next_run = None
    if cron_schedule:
        next_run = calculate_next_run(cron_schedule)
    
    # Create task
    task_id = str(uuid.uuid4())
    new_task = models.Task(
        task_id=task_id,
        name=name,
        description=description,
        config=config,
        capability_id=capability_id,
        platform_id=platform_id,
        created_by_id=str(current_user.user_id),
        notification_config_id=notification_config_id,
        next_run=next_run,
        timeout_seconds=timeout_seconds,
        cron_schedule=cron_schedule,
        proof_of_work_required=proof_of_work_required,
        is_active=True,
        is_hidden=False
    )
    
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    
    # If run_now, create TaskExecution immediately
    if run_now:
        execution_id = str(uuid.uuid4())
        execution = models.TaskExecution(
            execution_id=execution_id,
            task_id=task_id,
            created_by_id=str(current_user.user_id),
            status=models.TaskStatusEnum.BROADCASTED,
            is_hidden=False
        )
        db.add(execution)
        db.commit()
    
    return schemas.TaskResponse(
        task_id=str(new_task.task_id),
        name=str(new_task.name),
        description=new_task.description,
        platform_id=str(new_task.platform_id),
        capability_id=str(new_task.capability_id),
        created_by_username=str(current_user.username),
        config=new_task.config,
        cron_schedule=new_task.cron_schedule,
        notification_config_id=new_task.notification_config_id,
        next_run=new_task.next_run,  # type: ignore
        last_run=new_task.last_run,  # type: ignore
        timeout_seconds=int(new_task.timeout_seconds),
        proof_of_work_required=bool(new_task.proof_of_work_required),
        is_active=bool(new_task.is_active),
        created_at=new_task.created_at  # type: ignore
    )

@router.get("/", response_model=List[schemas.TaskResponse])
async def list_tasks(
    include_hidden: bool = False,
    capability_id: Optional[str] = Query(None),
    platform_id: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    List tasks with optional filters.
    
    - Regular users see only their own tasks
    - Admins see all tasks
    - Filters: capability_id, platform_id, is_active
    """
    query = db.query(models.Task)
    
    # Permission-based filtering
    if current_user.role.admin:
        # Admins see all
        if include_hidden and not can_see_hidden(current_user):
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to see hidden tasks"
            )
        if not include_hidden:
            query = query.filter(models.Task.is_hidden == False)
    else:
        # Users see only their own non-hidden tasks
        query = query.filter(
            models.Task.created_by_id == str(current_user.user_id),
            models.Task.is_hidden == False
        )
    
    # Apply filters
    if capability_id:
        query = query.filter(models.Task.capability_id == capability_id)
    if platform_id:
        query = query.filter(models.Task.platform_id == platform_id)
    if is_active is not None:
        query = query.filter(models.Task.is_active == is_active)
    
    tasks = query.all()
    
    return [
        schemas.TaskResponse(
            task_id=str(task.task_id),
            name=str(task.name),
            description=task.description,
            platform_id=str(task.platform_id),
            capability_id=str(task.capability_id),
            created_by_username=str(task.created_by.username),
            config=task.config,
            cron_schedule=task.cron_schedule,
            notification_config_id=task.notification_config_id,
            next_run=task.next_run,  # type: ignore
            last_run=task.last_run,  # type: ignore
            timeout_seconds=int(task.timeout_seconds),
            proof_of_work_required=bool(task.proof_of_work_required),
            is_active=bool(task.is_active),
            created_at=task.created_at  # type: ignore
        )
        for task in tasks
    ]

@router.get("/{task_id}", response_model=schemas.TaskResponse)
async def get_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get a specific task.
    
    - Users can view their own tasks
    - Admins can view any task
    """
    task = db.query(models.Task).filter(models.Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Permission check
    if str(task.created_by_id) != str(current_user.user_id) and not current_user.role.admin:
        raise HTTPException(
            status_code=403,
            detail="You can only view your own tasks"
        )
    
    # Hidden check
    if bool(task.is_hidden) and not can_see_hidden(current_user):
        raise HTTPException(status_code=404, detail="Task not found")
    
    return schemas.TaskResponse(
        task_id=str(task.task_id),
        name=str(task.name),
        description=task.description,
        platform_id=str(task.platform_id),
        capability_id=str(task.capability_id),
        created_by_username=str(task.created_by.username),
        config=task.config,
        cron_schedule=task.cron_schedule,
        notification_config_id=task.notification_config_id,
        next_run=task.next_run,  # type: ignore
        last_run=task.last_run,  # type: ignore
        timeout_seconds=int(task.timeout_seconds),
        proof_of_work_required=bool(task.proof_of_work_required),
        is_active=bool(task.is_active),
        created_at=task.created_at  # type: ignore
    )

@router.patch("/{task_id}", response_model=schemas.TaskResponse)
async def update_task(
    task_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    config: Optional[dict] = None,
    capability_id: Optional[str] = None,
    platform_id: Optional[str] = None,
    cron_schedule: Optional[str] = None,
    notification_config_id: Optional[str] = None,
    timeout_seconds: Optional[int] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Update a task (editable fields only).
    
    - Users can update their own tasks
    - Admins can update any task
    
    Editable fields: name, description, config, capability_id, platform_id,
                     cron_schedule, notification_config_id, timeout_seconds, is_active
    """
    task = db.query(models.Task).filter(models.Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Permission check
    if str(task.created_by_id) != str(current_user.user_id) and not current_user.role.admin:
        raise HTTPException(
            status_code=403,
            detail="You can only update your own tasks"
        )
    
    # Build update dict
    updates = {}
    if name is not None:
        updates["name"] = name
    if description is not None:
        updates["description"] = description
    if config is not None:
        updates["config"] = config
    if capability_id is not None:
        # Verify capability exists
        capability = db.query(models.Capability).filter(
            models.Capability.id == capability_id
        ).first()
        if not capability:
            raise HTTPException(status_code=404, detail="Capability not found")
        updates["capability_id"] = capability_id
    if platform_id is not None:
        # Verify platform exists
        platform = db.query(models.Platform).filter(
            models.Platform.id == platform_id
        ).first()
        if not platform:
            raise HTTPException(status_code=404, detail="Platform not found")
        updates["platform_id"] = platform_id
    if cron_schedule is not None:
        # Validate cron schedule
        try:
            next_run = calculate_next_run(cron_schedule)
            updates["cron_schedule"] = cron_schedule
            updates["next_run"] = next_run
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    if notification_config_id is not None:
        updates["notification_config_id"] = notification_config_id
    if timeout_seconds is not None:
        updates["timeout_seconds"] = timeout_seconds
    if is_active is not None:
        updates["is_active"] = is_active
    
    # Apply updates
    if updates:
        db.query(models.Task).filter(models.Task.task_id == task_id).update(updates)
        db.commit()
        db.refresh(task)
    
    return schemas.TaskResponse(
        task_id=str(task.task_id),
        name=str(task.name),
        description=task.description,
        platform_id=str(task.platform_id),
        capability_id=str(task.capability_id),
        created_by_username=str(task.created_by.username),
        config=task.config,
        cron_schedule=task.cron_schedule,
        notification_config_id=task.notification_config_id,
        next_run=task.next_run,  # type: ignore
        last_run=task.last_run,  # type: ignore
        timeout_seconds=int(task.timeout_seconds),
        proof_of_work_required=bool(task.proof_of_work_required),
        is_active=bool(task.is_active),
        created_at=task.created_at  # type: ignore
    )

@router.delete("/{task_id}", status_code=204)
async def soft_delete_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Soft delete a task (sets is_hidden=True).
    
    Cascades to all TaskExecutions (they also get hidden).
    
    - Users can soft delete their own tasks
    - Admins can soft delete any task
    """
    task = db.query(models.Task).filter(models.Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Permission check
    if str(task.created_by_id) != str(current_user.user_id) and not current_user.role.admin:
        raise HTTPException(
            status_code=403,
            detail="You can only delete your own tasks"
        )
    
    # Soft delete task
    db.query(models.Task).filter(models.Task.task_id == task_id).update({
        "is_hidden": True,
        "is_active": False
    })
    
    # Cascade: hide all task executions
    db.query(models.TaskExecution).filter(
        models.TaskExecution.task_id == task_id
    ).update({
        "is_hidden": True
    })
    
    db.commit()

@router.delete("/{task_id}/hard", status_code=204)
async def hard_delete_task(
    task_id: str,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_admin)
):
    """
    Hard delete a task (admin only).
    
    Cascades: deletes all TaskExecutions.
    WARNING: This cannot be undone!
    """
    task = db.query(models.Task).filter(models.Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Delete all task executions first (cascade)
    db.query(models.TaskExecution).filter(
        models.TaskExecution.task_id == task_id
    ).delete()
    
    # Delete task
    db.delete(task)
    db.commit()