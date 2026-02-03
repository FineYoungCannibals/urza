 # /urza/api/routes/bots.py
 # Bot management CRUD + Checkin

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime, UTC

from urza.db.schemas import (
    BotCreateRequest,
    BotCreateResponse,
    BotLookupResponse,
    BotCheckin,
    User
)
from auth import get_current_user, require_admin, check_bot_ownership
from urza.db.database import (
    get_platform_by_id,
    validate_capabilities_exist,
    create_bot,
    get_bot_by_id,
    get_bots_by_user,
    get_all_bots,
    soft_delete_bot,
    update_bot_last_checkin,
    get_username_by_user_id
)
from urza.core.bot_manager import (
    generate_bot_id,
    generate_s3_credentials,
    revoke_s3_credentials,
    create_telegram_bot,
    add_bot_to_channel
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# POST /bots - Create Bot
# ============================================================================

@router.post(
    "/",
    response_model=BotCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new bot"
)
async def create_new_bot(
    bot_request: BotCreateRequest,
    user: User = Depends(get_current_user)
):
    """
    Create a new bot.
    
    - Validates platform and capabilities exist
    - Generates S3 credentials via DigitalOcean Spaces
    - Creates Telegram bot via BotFather
    - Adds bot to Telegram channel
    - Returns credentials ONE TIME ONLY (never shown again)
    
    Permissions:
    - Any authenticated user can create bots
    - Only admins can create is_hidden=True bots
    """
    logger.info(f"User {user.username} creating bot")
    
    # Check if user is trying to create hidden bot without admin permission
    if bot_request.is_hidden and not user.role.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create hidden bots"
        )
    
    # Validate platform exists
    platform = await get_platform_by_id(bot_request.platform_id)
    if not platform:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Platform '{bot_request.platform_id}' does not exist"
        )
    
    # Validate all capabilities exist
    if not await validate_capabilities_exist(bot_request.capabilities):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more capabilities do not exist"
        )
    
    # Generate bot ID
    bot_id = generate_bot_id()
    logger.debug(f"Generated bot_id: {bot_id}")
    
    # Generate S3 credentials via DigitalOcean Spaces
    try:
        s3_access_key, s3_auth_key = await generate_s3_credentials(bot_id)
        logger.debug(f"Generated DO Spaces credentials for bot: {bot_id}")
    except Exception as e:
        logger.error(f"Failed to create DO Spaces credentials: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create S3 credentials: {str(e)}"
        )
    
    # Create Telegram bot via BotFather
    try:
        tg_bot_username, tg_bot_id, tg_bot_token = await create_telegram_bot(bot_id)
        logger.debug(f"Created Telegram bot: @{tg_bot_username} (ID: {tg_bot_id})")
    except Exception as e:
        logger.error(f"Failed to create Telegram bot: {str(e)}")
        # Cleanup: revoke DO Spaces keys since bot creation failed
        try:
            await revoke_s3_credentials(bot_id, s3_access_key)
        except:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create Telegram bot: {str(e)}"
        )
    
    # Add bot to Telegram channel
    try:
        await add_bot_to_channel(tg_bot_username)
        logger.info(f"Added bot @{tg_bot_username} to channel")
    except Exception as e:
        logger.warning(f"Failed to add bot to channel: {str(e)}")
        # Don't fail the whole operation, just log it
    
    # Prepare bot data for database
    bot_data = {
        "bot_id": bot_id,
        "created_by_id": user.user_id,
        "platform_id": bot_request.platform_id,
        "s3_access_key": s3_access_key,
        "s3_auth_key": s3_auth_key,
        "tg_bot_username": tg_bot_username,
        "tg_bot_token": tg_bot_token,
        "capabilities": bot_request.capabilities,
        "last_checkin": None,
        "created_at": datetime.now(UTC),
        "is_hidden": bot_request.is_hidden
    }
    
    # Save to database
    await create_bot(bot_data)
    
    logger.info(f"Bot created successfully: {bot_id}")
    
    # Return credentials (ONE TIME ONLY - never returned again)
    return BotCreateResponse(
        bot_id=bot_id,
        platform_id=bot_request.platform_id,
        s3_access_key=s3_access_key,
        s3_auth_key=s3_auth_key,
        tg_bot_username=tg_bot_username,
        tg_bot_token=tg_bot_token,
        capabilities=bot_request.capabilities
    )


# ============================================================================
# GET /bots - List Bots
# ============================================================================

@router.get(
    "/",
    response_model=List[BotLookupResponse],
    summary="List bots"
)
async def list_bots(user: User = Depends(get_current_user)):
    """
    List bots based on user permissions.
    
    Permissions:
    - Regular users: see only their own non-hidden bots
    - Admins: see all bots including hidden (soft-deleted) ones
    """
    logger.info(f"User {user.username} listing bots")
    
    # Admins see everything including hidden
    if user.role.admin:
        bots = await get_all_bots(include_hidden=True)
        logger.debug(f"Admin fetching all bots (including hidden)")
    # Regular users see only their own non-hidden bots
    else:
        bots = await get_bots_by_user(user.user_id, include_hidden=False)
        logger.debug(f"User fetching their own bots (excluding hidden)")
    
    # Convert to response format (no credentials)
    response = []
    for bot in bots:
        response.append(BotLookupResponse(
            bot_id=bot["bot_id"],
            created_by_username=await get_username_by_user_id(bot["created_by_id"]),
            tg_bot_username=bot["tg_bot_username"],
            platform_id=bot["platform_id"],
            capabilities=bot["capabilities"],
            created_at=bot["created_at"]
        ))
    
    logger.info(f"Returning {len(response)} bots")
    return response


# ============================================================================
# GET /bots/{bot_id} - Get Single Bot
# ============================================================================

@router.get(
    "/{bot_id}",
    response_model=BotLookupResponse,
    summary="Get bot details"
)
async def get_bot(
    bot_id: str,
    user: User = Depends(get_current_user)
):
    """
    Get details for a specific bot (no credentials returned).
    
    Permissions:
    - Regular users: only their own non-hidden bots
    - Admins: any bot including hidden
    """
    logger.info(f"User {user.username} fetching bot {bot_id}")
    
    # Fetch bot from database
    bot = await get_bot_by_id(bot_id)
    
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found"
        )
    
    # Check ownership and permissions
    check_bot_ownership(bot, user)
    
    # Return bot details (NO CREDENTIALS)
    return BotLookupResponse(
        bot_id=bot["bot_id"],
        created_by_username=await get_username_by_user_id(bot["created_by_id"]),
        tg_bot_username=bot["tg_bot_username"],
        platform_id=bot["platform_id"],
        capabilities=bot["capabilities"],
        created_at=bot["created_at"]
    )


# ============================================================================
# DELETE /bots/{bot_id} - Soft Delete Bot
# ============================================================================

@router.delete(
    "/{bot_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete bot (soft delete)"
)
async def delete_bot(
    bot_id: str,
    user: User = Depends(get_current_user)
):
    """
    Soft delete a bot by setting is_hidden=True.
    
    Permissions:
    - Users can delete their own bots
    - Admins can delete any bot
    """
    logger.info(f"User {user.username} deleting bot {bot_id}")
    
    # Fetch bot
    bot = await get_bot_by_id(bot_id)
    
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found"
        )
    
    # Check ownership (admins can delete any bot)
    check_bot_ownership(bot, user)
    
    # Soft delete
    await soft_delete_bot(bot_id)
    
    logger.info(f"Bot {bot_id} soft deleted successfully")
    return None


# ============================================================================
# POST /bots/{bot_id}/checkin - Bot Health Check (Admin Only)
# ============================================================================

@router.post(
    "/{bot_id}/checkin",
    status_code=status.HTTP_200_OK,
    summary="Update bot checkin timestamp (admin only)"
)
async def bot_checkin(
    bot_id: str,
    checkin: BotCheckin,
    user: User = Depends(require_admin)
):
    """
    Update bot's last_checkin timestamp for telemetry.
    
    Permissions:
    - Admin only
    """
    logger.info(f"Admin {user.username} updating checkin for bot {bot_id}")
    
    # Validate bot exists
    bot = await get_bot_by_id(bot_id)
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found"
        )
    
    # Validate bot_id matches
    if checkin.bot_id != bot_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="bot_id in path does not match bot_id in request body"
        )
    
    # Update last_checkin
    await update_bot_last_checkin(bot_id)
    
    logger.info(f"Bot {bot_id} checkin updated successfully")
    return {
        "bot_id": bot_id,
        "last_checkin": checkin.timestamp,
        "status": "updated"
    }