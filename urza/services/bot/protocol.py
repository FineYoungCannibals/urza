# protocol parsing
# urza/services/bot/protocol.py

"""
Bot communication protocol handlers.

Processes commands from remote worker bots:
- /claim - Bot claims a task execution
- /status - Bot sends progress update
- /complete - Bot reports successful completion
- /failed - Bot reports failure
"""

import json
import logging
from datetime import datetime, UTC
from telethon import events
from sqlalchemy.orm import Session

from urza.db import models

logger = logging.getLogger(__name__)


async def handle_claim(event: events.NewMessage.Event, SessionFactory) -> None:
    """
    Handle /claim command from bot workers.
    
    Expected format: /claim {"execution_id": "uuid", "bot_id": "uuid", "claimed_at": "ISO8601"}
    
    Updates:
    - execution.status -> IN_PROGRESS
    - execution.assigned_to -> bot_id
    - execution.claimed_at -> timestamp
    """
    db: Session = SessionFactory()
    
    try:
        # Parse message
        text = event.message.text
        json_str = text.replace('/claim', '').strip()
        data = json.loads(json_str)
        
        execution_id = data['execution_id']
        bot_id = data['bot_id']
        claimed_at = data.get('claimed_at', datetime.now(UTC))
        
        # Convert ISO string to datetime if needed
        if isinstance(claimed_at, str):
            claimed_at = datetime.fromisoformat(claimed_at.replace('Z', '+00:00'))
        
        # Validate bot exists and is active
        bot = db.query(models.Bot).filter_by(
            bot_id=bot_id,
            is_hidden=False
        ).first()
        
        if not bot:
            logger.warning(f"Unknown or inactive bot {bot_id} attempted to claim {execution_id}")
            return
        
        # Get execution
        execution = db.query(models.TaskExecution).filter_by(
            execution_id=execution_id
        ).first()
        
        if not execution:
            logger.warning(f"Bot {bot_id} claimed non-existent execution {execution_id}")
            return
        
        # Check if already claimed by another bot
        if execution.assigned_to and execution.assigned_to != bot_id: #type: ignore
            logger.warning(
                f"Bot {bot_id} attempted to claim execution {execution_id} "
                f"already assigned to {execution.assigned_to}"
            )
            return
        
        # Update execution
        execution.status = models.TaskStatusEnum.IN_PROGRESS  # type: ignore
        execution.assigned_to = bot_id  # type: ignore
        execution.claimed_at = claimed_at  # type: ignore
        
        # Update bot last_checkin
        bot.last_checkin = datetime.now(UTC)  # type: ignore
        
        db.commit()
        
        logger.info(f"Bot @{bot.tg_bot_username} claimed execution {execution_id}")
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in claim command: {e}")
    except KeyError as e:
        logger.error(f"Missing required field in claim: {e}")
    except Exception as e:
        logger.error(f"Error handling claim: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()


async def handle_status(event: events.NewMessage.Event, SessionFactory) -> None:
    """
    Handle /status command from bot workers.
    
    Expected format: /status {"execution_id": "uuid", "bot_id": "uuid", "message": "Processing..."}
    
    This is informational only - doesn't change execution status, just logs progress.
    Could be extended to store progress updates in a separate table if needed.
    """
    db: Session = SessionFactory()
    
    try:
        # Parse message
        text = event.message.text
        json_str = text.replace('/status', '').strip()
        data = json.loads(json_str)
        
        execution_id = data['execution_id']
        bot_id = data['bot_id']
        status_message = data.get('message', 'Working...')
        
        # Validate bot exists
        bot = db.query(models.Bot).filter_by(
            bot_id=bot_id,
            is_hidden=False
        ).first()
        
        if not bot:
            logger.warning(f"Status update from unknown bot {bot_id}")
            return
        
        # Validate execution exists
        execution = db.query(models.TaskExecution).filter_by(
            execution_id=execution_id
        ).first()
        
        if not execution:
            logger.warning(f"Status update for non-existent execution {execution_id}")
            return
        
        # Update bot last_checkin
        bot.last_checkin = datetime.now(UTC)  # type: ignore
        db.commit()
        
        logger.info(f"Bot @{bot.tg_bot_username} status for {execution_id}: {status_message}")
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in status command: {e}")
    except KeyError as e:
        logger.error(f"Missing required field in status: {e}")
    except Exception as e:
        logger.error(f"Error handling status: {e}", exc_info=True)
    finally:
        db.close()


async def handle_result(event: events.NewMessage.Event, SessionFactory) -> None:
    """
    Handle /complete and /failed commands from bot workers.
    
    Expected format: 
    /complete {"execution_id": "uuid", "bot_id": "uuid", "status": "completed", "results": {...}, "completed_at": "ISO8601"}
    /failed {"execution_id": "uuid", "bot_id": "uuid", "status": "failed", "error_message": "...", "completed_at": "ISO8601"}
    
    Updates:
    - execution.status -> COMPLETED or FAILED
    - execution.results -> results dict (if completed)
    - execution.error_message -> error message (if failed)
    - execution.completed_at -> timestamp
    """
    db: Session = SessionFactory()
    
    try:
        # Parse message
        text = event.message.text
        command = text.split()[0]  # /complete or /failed
        json_str = text.replace(command, '').strip()
        data = json.loads(json_str)
        
        execution_id = data['execution_id']
        bot_id = data['bot_id']
        status = data['status']  # "completed" or "failed"
        completed_at = data.get('completed_at', datetime.now(UTC))
        
        # Convert ISO string to datetime if needed
        if isinstance(completed_at, str):
            completed_at = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
        
        # Validate bot exists
        bot = db.query(models.Bot).filter_by(
            bot_id=bot_id,
            is_hidden=False
        ).first()
        
        if not bot:
            logger.warning(f"Result from unknown bot {bot_id}")
            return
        
        # Get execution
        execution = db.query(models.TaskExecution).filter_by(
            execution_id=execution_id
        ).first()
        
        if not execution:
            logger.warning(f"Result for non-existent execution {execution_id}")
            return
        
        # Verify this bot is assigned to this execution
        if execution.assigned_to != bot_id:
            logger.warning(
                f"Bot {bot_id} submitted result for execution {execution_id} "
                f"assigned to {execution.assigned_to}"
            )
            return
        
        # Update execution based on status
        if status == "completed":
            execution.status = models.TaskStatusEnum.COMPLETED  # type: ignore
            execution.results = data.get('results', {})  # type: ignore
            logger.info(f"Bot @{bot.tg_bot_username} completed execution {execution_id}")
        elif status == "failed":
            execution.status = models.TaskStatusEnum.FAILED  # type: ignore
            execution.error_message = data.get('error_message', 'Unknown error')  # type: ignore
            logger.warning(
                f"Bot @{bot.tg_bot_username} failed execution {execution_id}: "
                f"{execution.error_message}"
            )
        else:
            logger.error(f"Unknown status '{status}' in result from bot {bot_id}")
            return
        
        execution.completed_at = completed_at  # type: ignore
        
        # Update bot last_checkin
        bot.last_checkin = datetime.now(UTC)  # type: ignore
        
        db.commit()
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in result command: {e}")
    except KeyError as e:
        logger.error(f"Missing required field in result: {e}")
    except Exception as e:
        logger.error(f"Error handling result: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()