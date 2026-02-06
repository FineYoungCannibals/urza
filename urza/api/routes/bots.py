"""
Bot management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, UTC
import uuid
import logging

from urza.db.session import get_db
from urza.db import models
from urza.api import schemas
from urza.api.auth import get_current_user, check_resource_access, can_see_hidden, require_admin
from urza.core.bot_manager import create_telegram_bot, add_bot_to_channel, remove_bot_from_channel, delete_telegram_bot

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/bots", tags=["bots"])


@router.post("", response_model=schemas.BotCreateResponse, status_code=201)
async def create_bot(
    bot_request: schemas.BotCreateRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new bot via BotFather and add to Telegram channel.
    
    This process:
    1. Generates a unique bot_id
    2. Creates bot via BotFather (using Urza's Telegram client)
    3. Adds bot to Telegram channel as admin
    4. Stores bot in database
    5. Returns credentials (bot_id, username, token) - SHOWN ONCE ONLY
    
    The bot token is only returned in this response and cannot be retrieved again.
    """
    bot_id = str(uuid.uuid4())
    
    try:
        # Create bot via BotFather
        logger.info(f"User {current_user.username} creating bot {bot_id}")
        tg_username, tg_bot_id, tg_token = await create_telegram_bot(bot_id)
        
        if not tg_username or not tg_token:
            raise HTTPException(
                status_code=500,
                detail="Failed to create bot via BotFather"
            )
        
        # Add bot to Telegram channel
        logger.info(f"Adding bot @{tg_username} to channel")
        await add_bot_to_channel(tg_username)
        
        # Create bot record in database
        bot = models.Bot(
            bot_id=bot_id,
            tg_bot_username=tg_username,
            tg_bot_token=tg_token,
            created_by_id=current_user.user_id,
            created_at=datetime.now(UTC),
            is_hidden=False
        )
        
        db.add(bot)
        db.commit()
        db.refresh(bot)
        
        logger.info(f"Successfully created bot {bot_id} (@{tg_username}) for user {current_user.username}")
        
        return schemas.BotCreateResponse(
            bot_id=bot.bot_id,  # type: ignore
            tg_bot_username=bot.tg_bot_username,  # type: ignore
            tg_bot_token=bot.tg_bot_token  # type: ignore
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create bot for user {current_user.username}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create bot: {str(e)}"
        )


@router.get("", response_model=List[schemas.BotLookupResponse])
async def list_bots(
    include_hidden: bool = Query(False, description="Include soft-deleted bots (admin only)"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List bots.
    
    Access rules:
    - Users see only their own non-hidden bots
    - Admins see all non-hidden bots
    - Admins with can_see_hidden + include_hidden=true see all bots
    
    Note: Bot tokens are NOT included in list responses (only shown once at creation)
    """
    query = db.query(models.Bot, models.User).join(
        models.User, models.Bot.created_by_id == models.User.user_id
    )
    
    # Apply visibility filters
    if not current_user.role.admin:
        # Non-admins see only their own non-hidden bots
        query = query.filter(
            models.Bot.created_by_id == current_user.user_id
        ).filter(
            models.Bot.is_hidden.is_(False)
        )
    elif not include_hidden or not can_see_hidden(current_user):
        # Admins without can_see_hidden or without include_hidden flag
        query = query.filter(models.Bot.is_hidden.is_(False))
    # else: admin with can_see_hidden and include_hidden=true sees all
    
    results = query.all()
    
    return [
        schemas.BotLookupResponse(
            bot_id=bot.bot_id,  # type: ignore
            created_by_username=user.username,  # type: ignore
            tg_bot_username=bot.tg_bot_username,  # type: ignore
            created_at=bot.created_at  # type: ignore
        )
        for bot, user in results
    ]


@router.get("/{bot_id}", response_model=schemas.BotLookupResponse)
async def get_bot(
    bot_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a single bot by ID.
    
    Access rules:
    - Users can get their own bots
    - Admins can get any bot
    - Hidden bots only visible to users with can_see_hidden
    
    Note: Bot token is NOT included (only shown once at creation)
    """
    result = db.query(models.Bot, models.User).join(
        models.User, models.Bot.created_by_id == models.User.user_id
    ).filter(models.Bot.bot_id == bot_id).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    bot, user = result
    
    # Check access permissions
    check_resource_access(bot.created_by_id, current_user, bot.is_hidden)  # type: ignore
    
    return schemas.BotLookupResponse(
        bot_id=bot.bot_id,  # type: ignore
        created_by_username=user.username,  # type: ignore
        tg_bot_username=bot.tg_bot_username,  # type: ignore
        created_at=bot.created_at  # type: ignore
    )


@router.delete("/{bot_id}", status_code=204)
async def delete_bot(
    bot_id: str,
    permanent: bool = Query(False, description="Permanently delete from Telegram (admin only)"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a bot.
    
    Default behavior (permanent=False):
    - Soft delete in database (set is_hidden=True)
    - Remove from Telegram channel
    - Bot still exists in BotFather
    
    With permanent=True (admin only):
    - Soft delete in database
    - Remove from Telegram channel
    - Delete bot from BotFather entirely
    
    Access rules:
    - Users can delete their own bots (soft delete only)
    - Admins can delete any bot and use permanent deletion
    """
    bot = db.query(models.Bot).filter(
        models.Bot.bot_id == bot_id
    ).first()
    
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    # Check access permissions
    check_resource_access(bot.created_by_id, current_user, bot.is_hidden)  # type: ignore
    
    # Only admins can permanently delete
    if permanent and not current_user.role.admin:
        raise HTTPException(
            status_code=403,
            detail="Only admins can permanently delete bots"
        )
    
    try:
        # Remove from Telegram channel
        logger.info(f"Removing bot @{bot.tg_bot_username} from channel")
        await remove_bot_from_channel(bot.tg_bot_username)  # type: ignore
        
        # If permanent deletion requested, delete from BotFather
        if permanent:
            logger.info(f"Permanently deleting bot @{bot.tg_bot_username} from BotFather")
            await delete_telegram_bot(bot.tg_bot_username)  # type: ignore
        
        # Soft delete in database
        db.query(models.Bot).filter(
            models.Bot.bot_id == bot_id
        ).update({"is_hidden": True})
        db.commit()
        
        delete_type = "permanently deleted" if permanent else "soft-deleted"
        logger.info(f"User {current_user.username} {delete_type} bot {bot_id} (@{bot.tg_bot_username})")
        
        return None
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete bot {bot_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete bot: {str(e)}"
        )