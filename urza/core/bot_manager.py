# handles agent registrations (api key creation), and agent authorization, and helps guide the server on which agent type the agent is 
# /urza/core/bot_manager.py

import logging
import uuid
from core.spaces_client import DOAgent
from core.telegram_client import UrzaTGClient

logger = logging.getLogger(__name__)


def generate_bot_id() -> str:
    """Generate unique bot ID."""
    bot_id = str(uuid.uuid4())
    logger.debug(f"Generated bot_id: {bot_id}")
    return bot_id


async def generate_s3_credentials(bot_id: str) -> tuple[str, str]:
    """
    Generate S3 access key and auth key via DigitalOcean Spaces API.
    
    Args:
        bot_id: Bot identifier (used for key name)
        
    Returns:
        Tuple of (access_key, secret_key)
        
    Raises:
        Exception: If key creation fails
    """
    logger.info(f"Creating DO Spaces keys for bot: {bot_id}")
    
    try:
        # Initialize DO agent
        do_agent = DOAgent()
        
        # Create spaces keys with bot_id as name
        key_name = f"urza_bot_{bot_id}"
        response = do_agent.create_spaces_keys(key_name)
        
        # Extract credentials from response
        access_key = response['spaces_key']['access_key']
        secret_key = response['spaces_key']['secret_key']
        
        logger.info(f"Successfully created DO Spaces keys for bot: {bot_id}")
        return (access_key, secret_key)
        
    except Exception as e:
        logger.error(f"Failed to create DO Spaces keys for bot {bot_id}: {str(e)}")
        raise Exception(f"Failed to create S3 credentials: {str(e)}")


async def revoke_s3_credentials(bot_id: str, access_key: str) -> tuple[str, str]:
    """
    Revoke existing S3 credentials and create new ones.
    
    Args:
        bot_id: Bot identifier
        access_key: Existing access key to revoke
        
    Returns:
        Tuple of (new_access_key, new_secret_key)
        
    Raises:
        Exception: If key revocation/creation fails
    """
    logger.info(f"Revoking DO Spaces keys for bot: {bot_id}")
    
    try:
        do_agent = DOAgent()
        key_name = f"urza_bot_{bot_id}"
        
        # Revoke old key and create new one
        response = do_agent.revoke_spaces_keys(key_name, access_key)
        
        new_access_key = response['spaces_key']['access_key']
        new_secret_key = response['spaces_key']['secret_key']
        
        logger.info(f"Successfully revoked and recreated keys for bot: {bot_id}")
        return (new_access_key, new_secret_key)
        
    except Exception as e:
        logger.error(f"Failed to revoke/recreate keys for bot {bot_id}: {str(e)}")
        raise Exception(f"Failed to revoke S3 credentials: {str(e)}")


async def create_telegram_bot(bot_id: str) -> tuple[str, str, str]:
    """
    Create Telegram bot via BotFather using UrzaTGClient.
    
    Args:
        bot_id: Bot identifier (used to generate bot name/username)
        
    Returns:
        Tuple of (tg_bot_username, tg_bot_id, tg_bot_token)
        
    Raises:
        Exception: If bot creation fails
    """
    logger.info(f"Creating Telegram bot for bot_id: {bot_id}")
    
    try:
        # Initialize Telegram client
        tg_client = UrzaTGClient()
        await tg_client.connect()
        
        # Generate bot name and username
        # Bot username must end with 'bot'
        bot_name = f"Urza Bot {bot_id[:8]}"
        bot_username = f"urza_{bot_id[:8]}_bot"
        
        logger.debug(f"Creating bot with name='{bot_name}', username='@{bot_username}'")
        
        # Create bot via BotFather
        result = await tg_client.create_bot(bot_name, bot_username)
        
        if not result or result[0] is None:
            raise Exception("Failed to create Telegram bot - BotFather returned None")
        
        username, bot_tg_id, token = result
        
        if not token:
            raise Exception("Failed to parse bot token from BotFather response")
        
        logger.info(f"Successfully created Telegram bot: @{username} (ID: {bot_tg_id})")
        
        # Disconnect client
        await tg_client.disconnect()
        
        return (username, bot_tg_id, token)
        
    except Exception as e:
        logger.error(f"Failed to create Telegram bot for bot_id {bot_id}: {str(e)}")
        raise Exception(f"Failed to create Telegram bot: {str(e)}")


async def delete_telegram_bot(bot_username: str) -> bool:
    """
    Delete Telegram bot via BotFather.
    
    Args:
        bot_username: Bot username (without @)
        
    Returns:
        True if successful
        
    Raises:
        Exception: If deletion fails
    """
    logger.info(f"Deleting Telegram bot: @{bot_username}")
    
    try:
        tg_client = UrzaTGClient()
        await tg_client.connect()
        
        result = await tg_client.delete_bot(bot_username)
        
        await tg_client.disconnect()
        
        if result:
            logger.info(f"Successfully deleted Telegram bot: @{bot_username}")
            return True
        else:
            raise Exception("Delete operation returned False")
            
    except Exception as e:
        logger.error(f"Failed to delete Telegram bot @{bot_username}: {str(e)}")
        raise Exception(f"Failed to delete Telegram bot: {str(e)}")


async def revoke_telegram_bot_token(bot_username: str) -> str:
    """
    Revoke and regenerate Telegram bot token.
    
    Args:
        bot_username: Bot username (without @)
        
    Returns:
        New bot token
        
    Raises:
        Exception: If token revocation fails
    """
    logger.info(f"Revoking token for Telegram bot: @{bot_username}")
    
    try:
        tg_client = UrzaTGClient()
        await tg_client.connect()
        
        success, new_token = await tg_client.revoke_bot_token(bot_username)
        
        await tg_client.disconnect()
        
        if success and new_token:
            logger.info(f"Successfully revoked token for @{bot_username}")
            return new_token
        else:
            raise Exception("Token revocation failed or returned empty token")
            
    except Exception as e:
        logger.error(f"Failed to revoke token for @{bot_username}: {str(e)}")
        raise Exception(f"Failed to revoke bot token: {str(e)}")


async def add_bot_to_channel(bot_username: str) -> bool:
    """
    Add bot to Telegram channel as admin.
    
    Args:
        bot_username: Bot username (without @)
        
    Returns:
        True if successful
        
    Raises:
        Exception: If operation fails
    """
    logger.info(f"Adding bot @{bot_username} to channel")
    
    try:
        tg_client = UrzaTGClient()
        await tg_client.connect()
        
        result = await tg_client.add_bot_to_channel(bot_username)
        
        await tg_client.disconnect()
        
        if result:
            logger.info(f"Successfully added @{bot_username} to channel")
            return True
        else:
            raise Exception("Add to channel returned False")
            
    except Exception as e:
        logger.error(f"Failed to add @{bot_username} to channel: {str(e)}")
        raise Exception(f"Failed to add bot to channel: {str(e)}")


async def remove_bot_from_channel(bot_username: str) -> bool:
    """
    Ban/remove bot from Telegram channel.
    
    Args:
        bot_username: Bot username (without @)
        
    Returns:
        True if successful
        
    Raises:
        Exception: If operation fails
    """
    logger.info(f"Removing bot @{bot_username} from channel")
    
    try:
        tg_client = UrzaTGClient()
        await tg_client.connect()
        
        result = await tg_client.ban_from_channel(bot_username)
        
        await tg_client.disconnect()
        
        if result:
            logger.info(f"Successfully removed @{bot_username} from channel")
            return True
        else:
            raise Exception("Remove from channel returned False")
            
    except Exception as e:
        logger.error(f"Failed to remove @{bot_username} from channel: {str(e)}")
        raise Exception(f"Failed to remove bot from channel: {str(e)}")