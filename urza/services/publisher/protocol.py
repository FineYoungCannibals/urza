# urza/services/publisher/protocol.py

"""
Publisher Protocol - Defines how tasks are broadcast to Telegram for worker bots.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)


def format_task_broadcast(execution_id: str, task_id: str, task_config: Dict[str, Any], 
                         timeout_seconds: int, task_name: str = None) -> str:
    """
    Format a task execution for broadcast to Telegram channel.
    
    Bots will receive this message and self-filter based on their capabilities.
    """
    message = {
        "execution_id": execution_id,
        "task_id": task_id,
        "config": task_config,
        "timeout_seconds": timeout_seconds,
        "broadcast_time": datetime.utcnow().isoformat() + "Z"
    }
    
    if task_name:
        message["task_name"] = task_name
    
    # Format as code block for readability in Telegram
    json_str = json.dumps(message, indent=2)
    
    header = f"🎯 **New Task Available**\n"
    if task_name:
        header += f"**Task:** {task_name}\n"
    header += f"**Execution ID:** `{execution_id}`\n"
    header += f"**Timeout:** {timeout_seconds}s\n"
    header += f"\n**Configuration:**\n"
    
    formatted_message = f"{header}```json\n{json_str}\n```\n"
    formatted_message += f"\n💡 **To claim:** `/claim {{\"execution_id\": \"{execution_id}\", \"bot_id\": \"your-bot-id\"}}`"
    
    return formatted_message


def validate_task_config(task_config: Dict[str, Any]) -> bool:
    """
    Validate that task config has minimum required fields.
    """
    if not isinstance(task_config, dict):
        logger.error("Task config must be a dictionary")
        return False
    
    if not task_config:
        logger.error("Task config cannot be empty")
        return False
    
    return True