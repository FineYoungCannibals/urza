# API Key management
# /urza/api/routes/api_keys.py
"""
API Keys endpoint - manage API key authentication
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
    generate_api_key
)
from typing import List
import uuid
from datetime import datetime

router = APIRouter(prefix="/api-keys", tags=["api-keys"])

@router.post("/", response_model=schemas.APIKeyCreateResponse, status_code=201)
async def create_api_key(
    name: str,
    user_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Create a new API key.
    
    WARNING: The raw API key is only shown in this response once!
    
    - Regular users: Provide only 'name' to create a key for yourself
    - Admins: Provide 'user_id' to create a key for another user, 
              or omit it to create for yourself
    """
    # Determine target user
    if user_id:
        # Admin creating key for another user
        if not current_user.role.admin:
            raise HTTPException(
                status_code=403,
                detail="Only admins can create API keys for other users"
            )
        target_user_id = user_id
    else:
        # Creating key for self
        target_user_id = str(current_user.user_id)
    
    # Verify target user exists
    target_user = db.query(models.User).filter(
        models.User.user_id == target_user_id
    ).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")
    
    # Generate key
    raw_key, hashed_key = generate_api_key()
    
    # Create API key record
    key_id = str(uuid.uuid4())
    api_key = models.APIKey(
        id=key_id,
        name=name,
        hashed_key=hashed_key,
        user_id=target_user_id,
        created_by_id=str(current_user.user_id),
        is_active=True,
        is_hidden=False
    )
    
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    
    return schemas.APIKeyCreateResponse(
        id=key_id,
        name=name,
        api_key=raw_key,  # Show raw key only once!
        user_id=target_user_id,
        created_at=api_key.created_at  # type: ignore
    )

@router.get("/", response_model=List[schemas.APIKeyResponse])
async def list_api_keys(
    include_hidden: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    List API keys.
    
    - Regular users see only their own keys (non-hidden)
    - Admins see all keys (including hidden if they have can_see_hidden)
    """
    query = db.query(models.APIKey)
    
    if current_user.role.admin:
        # Admins see all keys
        if include_hidden and not can_see_hidden(current_user):
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to see hidden API keys"
            )
        if not include_hidden:
            query = query.filter(models.APIKey.is_hidden == False)
    else:
        # Regular users see only their own non-hidden keys
        query = query.filter(
            models.APIKey.user_id == str(current_user.user_id),
            models.APIKey.is_hidden == False
        )
    
    keys = query.all()
    
    return [
        schemas.APIKeyResponse(
            id=str(key.id),
            name=str(key.name),
            user_id=str(key.user_id),
            created_at=key.created_at,  # type: ignore
            last_used=key.last_used,  # type: ignore
            is_active=bool(key.is_active)
        )
        for key in keys
    ]

@router.get("/{key_id}", response_model=schemas.APIKeyResponse)
async def get_api_key(
    key_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get a specific API key.
    
    - Users can view their own keys
    - Admins can view any key
    """
    key = db.query(models.APIKey).filter(models.APIKey.id == key_id).first()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    # Permission check
    if str(key.user_id) != str(current_user.user_id) and not current_user.role.admin:
        raise HTTPException(
            status_code=403,
            detail="You can only view your own API keys"
        )
    
    # Hidden check
    if bool(key.is_hidden) and not can_see_hidden(current_user):
        raise HTTPException(status_code=404, detail="API key not found")
    
    return schemas.APIKeyResponse(
        id=str(key.id),
        name=str(key.name),
        user_id=str(key.user_id),
        created_at=key.created_at,  # type: ignore
        last_used=key.last_used,  # type: ignore
        is_active=bool(key.is_active)
    )

@router.patch("/{key_id}/deactivate", status_code=204)
async def deactivate_api_key(
    key_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Deactivate an API key (sets is_active=False).
    
    Key remains visible but cannot be used for authentication.
    
    - Users can deactivate their own keys
    - Admins can deactivate any key
    """
    key = db.query(models.APIKey).filter(models.APIKey.id == key_id).first()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    # Permission check
    if str(key.user_id) != str(current_user.user_id) and not current_user.role.admin:
        raise HTTPException(
            status_code=403,
            detail="You can only deactivate your own API keys"
        )
    
    # Deactivate
    db.query(models.APIKey).filter(models.APIKey.id == key_id).update({
        "is_active": False
    })
    db.commit()

@router.patch("/{key_id}/reactivate", status_code=204)
async def reactivate_api_key(
    key_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Reactivate an API key (sets is_active=True).
    
    - Users can reactivate their own keys
    - Admins can reactivate any key
    """
    key = db.query(models.APIKey).filter(models.APIKey.id == key_id).first()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    # Permission check
    if str(key.user_id) != str(current_user.user_id) and not current_user.role.admin:
        raise HTTPException(
            status_code=403,
            detail="You can only reactivate your own API keys"
        )
    
    # Cannot reactivate hidden keys
    if bool(key.is_hidden):
        raise HTTPException(
            status_code=400,
            detail="Cannot reactivate a deleted API key"
        )
    
    # Reactivate
    db.query(models.APIKey).filter(models.APIKey.id == key_id).update({
        "is_active": True
    })
    db.commit()

@router.delete("/{key_id}", status_code=204)
async def soft_delete_api_key(
    key_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Soft delete an API key (sets is_hidden=True and is_active=False).
    
    Key cannot be used and is hidden from listings.
    
    - Users can soft delete their own keys
    - Admins can soft delete any key
    """
    key = db.query(models.APIKey).filter(models.APIKey.id == key_id).first()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    # Permission check
    if str(key.user_id) != str(current_user.user_id) and not current_user.role.admin:
        raise HTTPException(
            status_code=403,
            detail="You can only delete your own API keys"
        )
    
    # Soft delete
    db.query(models.APIKey).filter(models.APIKey.id == key_id).update({
        "is_hidden": True,
        "is_active": False
    })
    db.commit()

@router.delete("/{key_id}/hard", status_code=204)
async def hard_delete_api_key(
    key_id: str,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_admin)
):
    """
    Hard delete an API key (admin only).
    
    Permanently removes key from database.
    WARNING: This cannot be undone!
    """
    key = db.query(models.APIKey).filter(models.APIKey.id == key_id).first()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    # Hard delete
    db.delete(key)
    db.commit()