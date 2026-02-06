# urza/db/redis_client.py
"""
Redis client for task queue management.
Provides singleton connection to Redis.
"""
import logging
import redis
from typing import Optional
from urza.config.settings import settings

logger = logging.getLogger(__name__)

_redis_client: Optional[redis.Redis] = None


def get_redis() -> redis.Redis:
    """
    Get or create Redis client singleton.
    
    Returns:
        redis.Redis: Connected Redis client
    """
    global _redis_client
    
    if _redis_client is None:
        logger.info(f"Connecting to Redis at {settings.redis_host}:{settings.redis_port}")
        
        _redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port, # type: ignore
            db=settings.redis_db,
            password=settings.redis_password,
            username=settings.redis_user,
            decode_responses=True,  # Return strings instead of bytes
            socket_connect_timeout=5,
            socket_keepalive=True,
            health_check_interval=30
        )
        
        # Test connection
        try:
            _redis_client.ping()
            logger.info("Redis connection established successfully")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            _redis_client = None
            raise
    
    return _redis_client


def close_redis():
    """
    Close Redis connection.
    Call during application shutdown.
    """
    global _redis_client
    
    if _redis_client is not None:
        logger.info("Closing Redis connection")
        _redis_client.close()
        _redis_client = None


def push_task_to_queue(execution_id: str, queue_name: str = "tasks:pending") -> bool:
    """
    Push a task execution ID to Redis queue.
    
    Args:
        execution_id: TaskExecution ID to queue
        queue_name: Redis list key (default: "tasks:pending")
    
    Returns:
        bool: True if successful
    """
    try:
        redis_client = get_redis()
        redis_client.lpush(queue_name, execution_id)
        logger.debug(f"Pushed execution {execution_id} to queue {queue_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to push execution {execution_id} to queue: {e}")
        return False


def pop_task_from_queue(queue_name: str = "tasks:pending", timeout: int = 0) -> Optional[str]:
    """
    Pop a task execution ID from Redis queue (blocking).
    
    Args:
        queue_name: Redis list key (default: "tasks:pending")
        timeout: Block timeout in seconds (0 = block indefinitely)
    
    Returns:
        str: execution_id if available, None if timeout
    """
    try:
        redis_client = get_redis()
        result = redis_client.brpop(queue_name, timeout=timeout) # type: ignore
        if result:
            _, execution_id = result # type: ignore
            logger.debug(f"Popped execution {execution_id} from queue {queue_name}")
            return execution_id
        return None
    except Exception as e:
        logger.error(f"Failed to pop from queue {queue_name}: {e}")
        return None


def get_queue_length(queue_name: str = "tasks:pending") -> int:
    """
    Get current length of Redis queue.
    
    Args:
        queue_name: Redis list key
    
    Returns:
        int: Number of items in queue
    """
    try:
        redis_client = get_redis()
        return redis_client.llen(queue_name) # type: ignore
    except Exception as e:
        logger.error(f"Failed to get queue length for {queue_name}: {e}")
        return 0