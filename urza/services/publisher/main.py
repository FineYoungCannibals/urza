# urza/services/publisher/main.py

"""
Urza Publisher Service

Flow:
1. Monitor Redis queue "tasks:pending"
2. Pop execution_id from queue
3. Fetch TaskExecution + Task from database
4. Validate execution is PENDING status
5. Format and broadcast to Telegram channel
6. Update execution status: PENDING → BROADCASTED
7. Set queued_at timestamp
"""

import asyncio
import logging
from datetime import datetime, UTC
from telethon import TelegramClient

from urza.services.publisher.settings import publisher_settings, setup_publisher_logging
from urza.services.publisher import protocol
from urza.db.session import SessionLocal
from urza.db import models
from urza.db.redis_client import pop_task_from_queue

logger = logging.getLogger(__name__)


class UrzaPublisher:
    """
    Publishes pending task executions from Redis to Telegram.
    """
    
    def __init__(self):
        self.client = TelegramClient(
            str(publisher_settings.session_file),
            publisher_settings.tg_api_id,
            publisher_settings.tg_api_hash
        )
        self.channel_id = int(publisher_settings.tg_channel_id)
        self.running = False
    
    async def start(self):
        """Start the publisher service"""
        logger.info("Starting Urza Publisher Service...")
        
        # Connect to Telegram
        await self.client.start()
        me = await self.client.get_me()
        logger.info(f"Connected to Telegram as: {me.first_name} (@{me.username})")
        
        self.running = True
        logger.info(f"Publishing to channel: {self.channel_id}")
        
        # Start polling loop
        await self.publisher_loop()
    
    async def publisher_loop(self):
        """
        Main loop: poll Redis, broadcast tasks, update database.
        """
        logger.info("Publisher loop started")
        
        while self.running:
            try:
                # Pop execution_id from Redis queue (blocking with timeout)
                execution_id = pop_task_from_queue(
                    queue_name="tasks:pending",
                    timeout=publisher_settings.poll_interval
                )
                
                if execution_id:
                    await self.process_execution(execution_id)
                else:
                    # No tasks in queue, wait before next poll
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error(f"Error in publisher loop: {e}", exc_info=True)
                await asyncio.sleep(publisher_settings.poll_interval)
    
    async def process_execution(self, execution_id: str):
        """
        Process a single task execution:
        1. Fetch from database
        2. Validate
        3. Broadcast to Telegram
        4. Update status: PENDING → BROADCASTED
        """
        db = SessionLocal()
        
        try:
            # Fetch execution and task
            result = db.query(models.TaskExecution, models.Task).join(
                models.Task, models.TaskExecution.task_id == models.Task.task_id
            ).filter(
                models.TaskExecution.execution_id == execution_id
            ).first()
            
            if not result:
                logger.error(f"Execution {execution_id} not found in database")
                return
            
            execution, task = result
            
            # Validate execution is in correct state
            if execution.status != models.TaskStatusEnum.PENDING:
                logger.warning(
                    f"Execution {execution_id} has status {execution.status}, "
                    f"expected PENDING. Skipping broadcast."
                )
                return
            
            # Validate task config
            if not protocol.validate_task_config(task.config):  # type: ignore
                logger.error(f"Invalid config for task {task.task_id}")
                execution.status = models.TaskStatusEnum.FAILED  # type: ignore
                execution.error_message = "Invalid task configuration"  # type: ignore
                db.commit()
                return
            
            # Format message
            message = protocol.format_task_broadcast(
                execution_id=execution.execution_id,  # type: ignore
                task_id=task.task_id,  # type: ignore
                task_config=task.config,  # type: ignore
                timeout_seconds=task.timeout_seconds,  # type: ignore
                task_name=task.name  # type: ignore
            )
            
            # Broadcast to Telegram
            logger.info(f"Broadcasting execution {execution_id} to channel {self.channel_id}")
            await self.client.send_message(self.channel_id, message, parse_mode='markdown')
            
            # Update execution status: PENDING → BROADCASTED
            execution.status = models.TaskStatusEnum.BROADCASTED  # type: ignore
            execution.queued_at = datetime.now(UTC)  # type: ignore
            
            db.commit()
            
            logger.info(f"Successfully broadcast execution {execution_id}")
            
        except Exception as e:
            logger.error(f"Error processing execution {execution_id}: {e}", exc_info=True)
            db.rollback()
        finally:
            db.close()
    
    async def stop(self):
        """Graceful shutdown"""
        logger.info("Stopping Urza Publisher Service...")
        self.running = False
        await self.client.disconnect()


async def main():
    """Entry point for publisher service"""
    setup_publisher_logging()
    
    publisher = UrzaPublisher()
    
    try:
        await publisher.start()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
        await publisher.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())