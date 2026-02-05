"""
Authentication and authorization middleware for Urza API
"""

import hashlib
import secrets
from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from urza.db.session import get_db
from urza.db import models
from datetime import datetime, UTC
import logging

logger = logging.getLogger(__name__)

# API Key header scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def hash_api_key(key: str) -> str:
    """Hash an API key for storage"""
    return hashlib.sha256(key.encode()).hexdigest()

def generate_api_key() -> tuple[str, str]:
    """
    Generate a new API key and its hash.
    
    Returns:
        (raw_key, hashed_key) - raw_key should be shown to user once
    """
    raw_key = f"urza_{secrets.token_urlsafe(32)}"
    hashed_key = hash_api_key(raw_key)
    return raw_key, hashed_key

async def get_current_user(
    api_key: str = Security(api_key_header),
    db: Session = Depends(get_db)
) -> models.User:
    """
    Validate API key and return current user.
    
    Raises:
        HTTPException: If API key is invalid or user not found
    """
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"}
        )
    
    # Hash the provided key
    hashed_key = hash_api_key(api_key)
    
    # Look up API key
    api_key_record = db.query(models.APIKey).filter_by(
        hashed_key=hashed_key,
        is_active=True,
        is_hidden=False
    ).first()
    
    if not api_key_record:
        logger.warning(f"Invalid API key attempt")
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    
    # Get the user
    user = db.query(models.User).filter_by(
        user_id=api_key_record.user_id,
        is_active=True,
        is_hidden=False
    ).first()
    
    if not user:
        logger.warning(f"API key valid but user not found or inactive: {api_key_record.user_id}")
        raise HTTPException(
            status_code=401,
            detail="User not found or inactive"
        )
    
    # Update last_used timestamp
    db.query(models.APIKey).filter_by(id=api_key_record.id).update({"last_used": datetime.now(UTC)})
    db.commit()
    
    logger.info(f"Authenticated user: {user.username} (role: {user.role_name})")
    return user

async def require_admin(
    current_user: models.User = Depends(get_current_user)
) -> models.User:
    """
    Require that current user is an admin.
    
    Raises:
        HTTPException: If user is not an admin
    """
    if not current_user.role.admin:
        logger.warning(f"Non-admin user attempted admin action: {current_user.username}")
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    return current_user

def can_see_hidden(user: models.User) -> bool:
    """Check if user can see soft-deleted (hidden) items"""
    return user.role.can_see_hidden

def check_resource_access(
    resource_owner_id: str,
    current_user: models.User,
    is_hidden: bool = False
) -> bool:
    """
    Check if current user can access a resource.
    
    Rules:
    - Hidden resources require can_see_hidden permission (otherwise 404)
    - Admins can access anything
    - Users can access their own resources
    
    Returns:
        True if access allowed
    
    Raises:
        HTTPException: If access denied
    """
    # Hidden check - return 404 if user can't see hidden items
    if is_hidden and not can_see_hidden(current_user):
        raise HTTPException(status_code=404, detail="Resource not found")
    
    # Admin can access everything
    if current_user.role.admin:
        return True
    
    # User can access their own resources
    if resource_owner_id == current_user.user_id:
        return True
    
    raise HTTPException(
        status_code=403,
        detail="You don't have permission to access this resource"
    )