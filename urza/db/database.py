# /urza/db/database.py

import logging
import pymysql
import json
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, UTC
from urza.config.settings import settings

logger = logging.getLogger(__name__)


# ============================================================================
# Connection Management
# ============================================================================

class DatabaseConnection:
    """Singleton database connection manager"""
    
    _connection = None
    
    @classmethod
    def get_connection(cls):
        """Get or create database connection"""
        if cls._connection is None or not cls._connection.open:
            logger.info(f"Connecting to MySQL: {MYSQL_USER}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}")
            cls._connection = pymysql.connect(
                host=MYSQL_HOST,
                port=MYSQL_PORT,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                database=MYSQL_DB,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=False
            )
            logger.info("Database connection established")
        return cls._connection
    
    @classmethod
    def close_connection(cls):
        """Close database connection"""
        if cls._connection and cls._connection.open:
            cls._connection.close()
            logger.info("Database connection closed")
            cls._connection = None


# ============================================================================
# Platform Operations
# ============================================================================

async def get_platform_by_id(platform_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch platform by ID.
    
    Returns:
        Platform dict or None
    """
    logger.debug(f"Fetching platform: {platform_id}")
    
    connection = DatabaseConnection.get_connection()
    cursor = connection.cursor()
    
    try:
        cursor.execute(
            "SELECT * FROM platforms WHERE id = %s",
            (platform_id,)
        )
        result = cursor.fetchone()
        return result
    
    except Exception as e:
        logger.error(f"Database error fetching platform {platform_id}: {str(e)}")
        return None
    
    finally:
        cursor.close()


async def create_platform(platform_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new platform.
    
    Args:
        platform_data: Dict with id, name, description, os_major_version
    """
    logger.info(f"Creating platform: {platform_data['id']}")
    
    connection = DatabaseConnection.get_connection()
    cursor = connection.cursor()
    
    try:
        cursor.execute(
            """
            INSERT INTO platforms (id, name, description, os_major_version)
            VALUES (%s, %s, %s, %s)
            """,
            (
                platform_data['id'],
                platform_data['name'],
                platform_data['description'],
                platform_data['os_major_version']
            )
        )
        connection.commit()
        return platform_data
    
    except Exception as e:
        connection.rollback()
        logger.error(f"Database error creating platform: {str(e)}")
        raise
    
    finally:
        cursor.close()


# ============================================================================
# Capability Operations
# ============================================================================

async def get_capability_by_id(capability_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch capability by ID.
    
    Returns:
        Capability dict or None
    """
    logger.debug(f"Fetching capability: {capability_id}")
    
    connection = DatabaseConnection.get_connection()
    cursor = connection.cursor()
    
    try:
        cursor.execute(
            "SELECT * FROM capabilities WHERE id = %s",
            (capability_id,)
        )
        result = cursor.fetchone()
        return result
    
    except Exception as e:
        logger.error(f"Database error fetching capability {capability_id}: {str(e)}")
        return None
    
    finally:
        cursor.close()


async def validate_capabilities_exist(capability_ids: List[str]) -> bool:
    """
    Check if all capability IDs exist.
    
    Returns:
        True if all exist, False otherwise
    """
    logger.debug(f"Validating capabilities: {capability_ids}")
    
    if not capability_ids:
        return False
    
    connection = DatabaseConnection.get_connection()
    cursor = connection.cursor()
    
    try:
        placeholders = ','.join(['%s'] * len(capability_ids))
        cursor.execute(
            f"SELECT COUNT(*) as count FROM capabilities WHERE id IN ({placeholders})",
            capability_ids
        )
        result = cursor.fetchone()

        if result is None:
            logger.warning("Query returned no results")
            return False
        return result['count'] == len(capability_ids)
    
    except Exception as e:
        logger.error(f"Database error validating capabilities: {str(e)}")
        return False
    
    finally:
        cursor.close()


async def create_capability(capability_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new capability.
    
    Args:
        capability_data: Dict with id, name, version, description
    """
    logger.info(f"Creating capability: {capability_data['id']}")
    
    connection = DatabaseConnection.get_connection()
    cursor = connection.cursor()
    
    try:
        cursor.execute(
            """
            INSERT INTO capabilities (id, name, version, description)
            VALUES (%s, %s, %s, %s)
            """,
            (
                capability_data['id'],
                capability_data['name'],
                capability_data['version'],
                capability_data['description']
            )
        )
        connection.commit()
        return capability_data
    
    except Exception as e:
        connection.rollback()
        logger.error(f"Database error creating capability: {str(e)}")
        raise
    
    finally:
        cursor.close()


# ============================================================================
# Bot Operations
# ============================================================================

async def create_bot(bot_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Insert bot into database.
    
    Args:
        bot_data: Dictionary with bot fields
    """
    logger.info(f"Creating bot: {bot_data['bot_id']}")
    
    connection = DatabaseConnection.get_connection()
    cursor = connection.cursor()
    
    try:
        # Convert capabilities list to JSON string
        capabilities_json = json.dumps(bot_data['capabilities'])
        
        cursor.execute(
            """
            INSERT INTO bots (
                bot_id, created_by_id, platform_id, s3_access_key, s3_auth_key,
                tg_bot_username, tg_bot_token, capabilities, last_checkin, 
                created_at, is_hidden
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                bot_data['bot_id'],
                bot_data['created_by_id'],
                bot_data['platform_id'],
                bot_data['s3_access_key'],
                bot_data['s3_auth_key'],
                bot_data['tg_bot_username'],
                bot_data['tg_bot_token'],
                capabilities_json,
                bot_data.get('last_checkin'),
                bot_data['created_at'],
                bot_data.get('is_hidden', False)
            )
        )
        connection.commit()
        return bot_data
    
    except Exception as e:
        connection.rollback()
        logger.error(f"Database error creating bot: {str(e)}")
        raise
    
    finally:
        cursor.close()


async def get_bot_by_id(bot_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch bot by ID.
    
    Returns:
        Bot dict or None
    """
    logger.debug(f"Fetching bot: {bot_id}")
    
    connection = DatabaseConnection.get_connection()
    cursor = connection.cursor()
    
    try:
        cursor.execute(
            "SELECT * FROM bots WHERE bot_id = %s",
            (bot_id,)
        )
        result = cursor.fetchone()
        
        if result:
            # Parse JSON capabilities back to list
            result['capabilities'] = json.loads(result['capabilities'])
        
        return result
    
    except Exception as e:
        logger.error(f"Database error fetching bot {bot_id}: {str(e)}")
        return None
    
    finally:
        cursor.close()


async def get_bots_by_user(user_id: str, include_hidden: bool = False) -> List[Dict[str, Any]]:
    """
    Fetch all bots created by a user.
    
    Args:
        user_id: User ID
        include_hidden: Whether to include soft-deleted bots
    """
    logger.debug(f"Fetching bots for user: {user_id}, include_hidden={include_hidden}")
    
    connection = DatabaseConnection.get_connection()
    cursor = connection.cursor()
    
    try:
        query = "SELECT * FROM bots WHERE created_by_id = %s"
        params = [user_id]
        
        if not include_hidden:
            query += " AND is_hidden = FALSE"
        
        cursor.execute(query, params)
        results = cursor.fetchall()

        if results is None:
            return []
        
        # Parse JSON capabilities for each bot
        for bot in results:
            bot['capabilities'] = json.loads(bot['capabilities'])
        
        return list(results) if results else []
    
    except Exception as e:
        logger.error(f"Database error fetching bots for user {user_id}: {str(e)}")
        return []
    
    finally:
        cursor.close()


async def get_all_bots(include_hidden: bool = False) -> List[Dict[str, Any]]:
    """
    Fetch all bots (admin function).
    
    Args:
        include_hidden: Whether to include soft-deleted bots
    """
    logger.debug(f"Fetching all bots, include_hidden={include_hidden}")
    
    connection = DatabaseConnection.get_connection()
    cursor = connection.cursor()
    
    try:
        query = "SELECT * FROM bots"
        if not include_hidden:
            query += " WHERE is_hidden = FALSE"
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        # Parse JSON capabilities for each bot
        for bot in results:
            bot['capabilities'] = json.loads(bot['capabilities'])
        
        return list(results) if results else []
    
    except Exception as e:
        logger.error(f"Database error fetching all bots: {str(e)}")
        return []
    
    finally:
        cursor.close()


async def soft_delete_bot(bot_id: str) -> bool:
    """
    Soft delete bot by setting is_hidden=True.
    
    Returns:
        True if successful
    """
    logger.info(f"Soft deleting bot: {bot_id}")
    
    connection = DatabaseConnection.get_connection()
    cursor = connection.cursor()
    
    try:
        cursor.execute(
            "UPDATE bots SET is_hidden = TRUE WHERE bot_id = %s",
            (bot_id,)
        )
        connection.commit()
        affected = cursor.rowcount
        return affected > 0
    
    except Exception as e:
        connection.rollback()
        logger.error(f"Database error soft deleting bot {bot_id}: {str(e)}")
        return False
    
    finally:
        cursor.close()


async def update_bot_last_checkin(bot_id: str) -> bool:
    """
    Update bot's last_checkin timestamp.
    
    Returns:
        True if successful
    """
    logger.info(f"Updating checkin for bot: {bot_id}")
    
    connection = DatabaseConnection.get_connection()
    cursor = connection.cursor()
    
    try:
        cursor.execute(
            "UPDATE bots SET last_checkin = %s WHERE bot_id = %s",
            (datetime.now(UTC), bot_id)
        )
        connection.commit()
        affected = cursor.rowcount
        return affected > 0
    
    except Exception as e:
        connection.rollback()
        logger.error(f"Database error updating checkin for bot {bot_id}: {str(e)}")
        return False
    
    finally:
        cursor.close()


# ============================================================================
# User Operations
# ============================================================================

async def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get user by ID with role information.
    
    Returns:
        User dict with role or None
    """
    logger.debug(f"Fetching user: {user_id}")
    
    connection = DatabaseConnection.get_connection()
    cursor = connection.cursor()
    
    try:
        cursor.execute(
            """
            SELECT u.*, r.description as role_description, r.admin, 
                   r.can_create_hidden, r.can_see_hidden
            FROM users u
            JOIN user_roles r ON u.role_name = r.name
            WHERE u.user_id = %s
            """,
            (user_id,)
        )
        result = cursor.fetchone()
        return result
    
    except Exception as e:
        logger.error(f"Database error fetching user {user_id}: {str(e)}")
        return None
    
    finally:
        cursor.close()


async def get_username_by_user_id(user_id: str) -> str:
    """
    Get username from user_id.
    
    Returns:
        Username string
    """
    logger.debug(f"Fetching username for user_id: {user_id}")
    
    connection = DatabaseConnection.get_connection()
    cursor = connection.cursor()
    
    try:
        cursor.execute(
            "SELECT username FROM users WHERE user_id = %s",
            (user_id,)
        )
        result = cursor.fetchone()
        return result['username'] if result else "unknown"
    
    except Exception as e:
        logger.error(f"Database error fetching username for {user_id}: {str(e)}")
        return "unknown"
    
    finally:
        cursor.close()


async def create_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new user.
    
    Args:
        user_data: Dict with user_id, username, role_name, description, created_by_id
    """
    logger.info(f"Creating user: {user_data['username']}")
    
    connection = DatabaseConnection.get_connection()
    cursor = connection.cursor()
    
    try:
        cursor.execute(
            """
            INSERT INTO users (user_id, username, role_name, description, created_by_id, is_active, is_hidden)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                user_data['user_id'],
                user_data['username'],
                user_data['role_name'],
                user_data.get('description'),
                user_data['created_by_id'],
                user_data.get('is_active', True),
                user_data.get('is_hidden', False)
            )
        )
        connection.commit()
        return user_data
    
    except Exception as e:
        connection.rollback()
        logger.error(f"Database error creating user: {str(e)}")
        raise
    
    finally:
        cursor.close()


# ============================================================================
# Role Operations
# ============================================================================

async def get_role_by_name(role_name: str) -> Optional[Dict[str, Any]]:
    """
    Get role by name.
    
    Returns:
        Role dict or None
    """
    logger.debug(f"Fetching role: {role_name}")
    
    connection = DatabaseConnection.get_connection()
    cursor = connection.cursor()
    
    try:
        cursor.execute(
            "SELECT * FROM user_roles WHERE name = %s",
            (role_name,)
        )
        result = cursor.fetchone()
        return result
    
    except Exception as e:
        logger.error(f"Database error fetching role {role_name}: {str(e)}")
        return None
    
    finally:
        cursor.close()


async def create_role(role_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new role.
    
    Args:
        role_data: Dict with name, description, admin, can_create_hidden, can_see_hidden
    """
    logger.info(f"Creating role: {role_data['name']}")
    
    connection = DatabaseConnection.get_connection()
    cursor = connection.cursor()
    
    try:
        cursor.execute(
            """
            INSERT INTO user_roles (name, description, admin, can_create_hidden, can_see_hidden)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                role_data['name'],
                role_data['description'],
                role_data.get('admin', False),
                role_data.get('can_create_hidden', False),
                role_data.get('can_see_hidden', False)
            )
        )
        connection.commit()
        return role_data
    
    except Exception as e:
        connection.rollback()
        logger.error(f"Database error creating role: {str(e)}")
        raise
    
    finally:
        cursor.close()


# ============================================================================
# API Key Operations
# ============================================================================

async def get_api_key_by_hashed_key(hashed_key: str) -> Optional[Dict[str, Any]]:
    """
    Get API key by hashed key.
    
    Returns:
        API key dict or None
    """
    logger.debug(f"Fetching API key by hash")
    
    connection = DatabaseConnection.get_connection()
    cursor = connection.cursor()
    
    try:
        cursor.execute(
            """
            SELECT * FROM api_keys 
            WHERE hashed_key = %s AND is_active = TRUE
            """,
            (hashed_key,)
        )
        result = cursor.fetchone()
        return result
    
    except Exception as e:
        logger.error(f"Database error fetching API key: {str(e)}")
        return None
    
    finally:
        cursor.close()


async def update_api_key_last_used(key_id: str) -> bool:
    """
    Update API key's last_used timestamp.
    
    Returns:
        True if successful
    """
    connection = DatabaseConnection.get_connection()
    cursor = connection.cursor()
    
    try:
        cursor.execute(
            "UPDATE api_keys SET last_used = %s WHERE id = %s",
            (datetime.now(UTC), key_id)
        )
        connection.commit()
        affected = cursor.rowcount
        return affected > 0
    
    except Exception as e:
        connection.rollback()
        logger.error(f"Database error updating API key last_used: {str(e)}")
        return False
    
    finally:
        cursor.close()


async def create_api_key(key_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new API key.
    
    Args:
        key_data: Dict with id, name, hashed_key, user_id, created_by_id
    """
    logger.info(f"Creating API key: {key_data['name']}")
    
    connection = DatabaseConnection.get_connection()
    cursor = connection.cursor()
    
    try:
        cursor.execute(
            """
            INSERT INTO api_keys (id, name, hashed_key, user_id, created_by_id, is_active, is_hidden)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                key_data['id'],
                key_data['name'],
                key_data['hashed_key'],
                key_data['user_id'],
                key_data['created_by_id'],
                key_data.get('is_active', True),
                key_data.get('is_hidden', False)
            )
        )
        connection.commit()
        return key_data
    
    except Exception as e:
        connection.rollback()
        logger.error(f"Database error creating API key: {str(e)}")
        raise
    
    finally:
        cursor.close()