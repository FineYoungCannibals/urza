# /urza/api/auth.py

import logging
from typing import Optional
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from urza.db.schemas import User, UserRole

logger = logging.getLogger(__name__)
security = HTTPBearer()


async def verify_api_key(api_key: str) -> User:
    """
    Verify API key and return User object.
    
    TODO: Implement
    1. Hash the incoming api_key
    2. Look up APIKey in database by hashed_key
    3. Check is_active = True
    4. Update last_used timestamp
    5. Get associated User with Role
    6. Return User object
    
    Args:
        api_key: Raw API key from Authorization header
        
    Returns:
        User object with role information
        
    Raises:
        HTTPException: 401 if invalid/inactive key
    """
    logger.debug(f"Verifying API key: {api_key[:8]}...")
    
    # TODO: Database lookup
    # hashed_key = hash_api_key(api_key)
    # api_key_record = db.query(APIKey).filter(
    #     APIKey.hashed_key == hashed_key,
    #     APIKey.is_active == True
    # ).first()
    # 
    # if not api_key_record:
    #     raise HTTPException(status_code=401, detail="Invalid API key")
    # 
    # # Update last_used
    # api_key_record.last_used = datetime.now(UTC)
    # db.commit()
    # 
    # # Get user with role
    # user = db.query(User).filter(User.user_id == api_key_record.user_id).first()
    # return user
    
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="API key verification not yet implemented"
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> User:
    """
    Extract and verify current user from Authorization header.
    
    Usage in routes:
        async def my_route(user: User = Depends(get_current_user)):
    """
    api_key = credentials.credentials
    user = await verify_api_key(api_key)
    return user


async def require_admin(user: User = Security(get_current_user)) -> User:
    """
    Require user to be admin.
    
    Usage:
        async def admin_route(user: User = Depends(require_admin)):
    """
    if not user.role.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user


def check_bot_ownership(bot, user: User) -> bool:
    """
    Check if user owns the bot or is admin.
    
    Args:
        bot: Bot object from database
        user: Current user
        
    Returns:
        True if user can access
        
    Raises:
        HTTPException: 403 if not owner and not admin
        HTTPException: 404 if bot is hidden and user is not admin
    """
    # If bot is hidden (soft deleted), only admins can see it
    if bot.is_hidden and not user.role.admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found"
        )
    
    # Admins can access any bot
    if user.role.admin:
        return True
    
    # Regular users must own the bot
    if bot.created_by_id != user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: not bot owner"
        )
    
    return True