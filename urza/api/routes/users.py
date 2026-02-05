"""
Users endpoint - manage user accounts
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from urza.db.session import get_db
from urza.api import schemas
from urza.db import models
from urza.api.auth import (
    get_current_user,
    require_admin,
    can_see_hidden,
    check_resource_access
)
from typing import List
import uuid

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=schemas.UserResponse)
async def get_current_user_info(
    current_user: models.User = Depends(get_current_user)
):
    """Get information about the currently authenticated user"""
    return schemas.UserResponse(
        user_id=str(current_user.user_id),
        username=str(current_user.username),
        created_by_username=str(current_user.created_by.username),
        role_name=str(current_user.role_name),
        description=str(current_user.description) if current_user.description is not None else None,
        created_at=current_user.created_at, # type: ignore
        is_active=bool(current_user.is_active)
    )

@router.get("/", response_model=List[schemas.UserResponse])
async def list_users(
    include_hidden: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    List users.
    
    - Regular users only see themselves
    - Admins see all users
    - include_hidden: Show soft-deleted users (requires can_see_hidden)
    """
    query = db.query(models.User)
    
    if current_user.role.admin:
        # Admins see all or all non-hidden
        if include_hidden and not can_see_hidden(current_user):
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to see hidden users"
            )
        if not include_hidden:
            query = query.filter(models.User.is_hidden == False)
    else:
        # Regular users only see themselves (non-hidden)
        query = query.filter(
            models.User.user_id == current_user.user_id,
            models.User.is_hidden == False
        )
    
    users = query.all()
    
    return [
        schemas.UserResponse(
            user_id=str(user.user_id),
            username=str(user.username),
            created_by_username=str(user.created_by.username),
            role_name=str(user.role_name),
            description=str(user.description) if user.description is not None else None,
            created_at=user.created_at, # type: ignore
            is_active=bool(user.is_active)
        )
        for user in users
    ]


@router.post("/", response_model=schemas.UserResponse, status_code=201)
async def create_user(
    username: str,
    role_name: str,
    description: str | None = None,
    is_active: bool = True,
    is_hidden: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin)
):
    """
    Create a new user (admin only).
    
    Only admins can create users.
    """
    # Check if username already exists
    existing = db.query(models.User).filter(models.User.username == username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Verify role exists
    role = db.query(models.UserRole).filter(models.UserRole.name == role_name).first()
    if not role:
        raise HTTPException(status_code=400, detail=f"Role '{role_name}' not found")
    
    # Create new user
    new_user_id = str(uuid.uuid4())
    new_user = models.User(
        user_id=new_user_id,
        username=username,
        role_name=role_name,
        description=description,
        created_by_id=str(current_user.user_id),
        is_active=is_active,
        is_hidden=is_hidden
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return schemas.UserResponse(
        user_id=str(new_user.user_id),
        username=str(new_user.username),
        created_by_username=str(current_user.username),
        role_name=str(new_user.role_name),
        description=str(new_user.description) if new_user is not None else None,
        created_at=new_user.created_at,  # type: ignore
        is_active=bool(new_user.is_active)
    )


@router.get("/{user_id}", response_model=schemas.UserResponse)
async def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get a specific user.
    
    - Users can view themselves
    - Admins can view anyone
    """
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check access
    check_resource_access(str(user.user_id), current_user, bool(user.is_hidden))
    
    return schemas.UserResponse(
        user_id=str(user.user_id),
        username=str(user.username),
        created_by_username=str(user.created_by.username),
        role_name=str(user.role_name),
        description=str(user.description) if user.description is None else None,
        created_at=user.created_at, # type: ignore
        is_active=bool(user.is_active)
    )

@router.delete("/{user_id}", status_code=204)
async def soft_delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_admin)
):
    """
    Soft delete a user (admin only).
    
    Sets is_hidden=True and is_active=False.
    """
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent deleting yourself
    if str(user.user_id) == str(_admin.user_id):
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    # Soft delete using update
    db.query(models.User).filter(models.User.user_id == user_id).update({
        "is_hidden": True,
        "is_active": False
    })
    db.commit()

@router.delete("/{user_id}/hard", status_code=204)
async def hard_delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_admin)
):
    """
    Hard delete a user (admin only).
    
    Permanently removes user from database.
    WARNING: This cannot be undone!
    """
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent deleting yourself
    if str(user.user_id) == str(_admin.user_id):
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    # Hard delete
    db.delete(user)
    db.commit()