# Monitor DB for Tasks that need to have Task Executions published to queue
# Moniotor DB for TaskExecutions past SLA, update them with TIMEOUT status
# urza/services/orchestrator/main.py

"""
Urza Orchestrator Service

Responsibilities:
1. Cron Evaluation - Check tasks with cron schedules and create executions when due
2. Timeout Monitoring - Check for executions that have exceeded their timeout
"""

import asyncio
import logging
from datetime import datetime, UTC
import uuid
from croniter import croniter

from urza.services.orchestrator.settings import orchestrator_settings, setup_orchestrator_logging
from urza.db.session import SessionLocal
from urza.db import models
from urza.db.redis_client import push_task_to_queue

logger = logging.getLogger(__name__)


class UrzaOrchestrator:
    """
    Orchestrates task scheduling and timeout monitoring.
    """
    
    def __init__(self):
        self.running = False
        self.cron_task = None
        self.timeout_task = None
    
    async def start(self):
        """Start the orchestrator service"""
        logger.info("Starting Urza Orchestrator Service...")
        
        self.running = True
        
        # Start both monitoring tasks
        self.cron_task = asyncio.create_task(self.cron_evaluator())
        self.timeout_task = asyncio.create_task(self.timeout_monitor())
        
        logger.info("Orchestrator running - monitoring cron schedules and timeouts")
        
        # Wait for both tasks
        await asyncio.gather(self.cron_task, self.timeout_task)
    
    async def cron_evaluator(self):
        """
        Periodically check for tasks with cron schedules that are due to run.
        Creates TaskExecutions and pushes to Redis queue.
        """
        logger.info("Cron evaluator started")
        
        while self.running:
            try:
                db = SessionLocal()
                now = datetime.now(UTC)
                
                # Find active tasks with cron schedules where next_run <= now
                tasks = db.query(models.Task).filter(
                    models.Task.is_active.is_(True),
                    models.Task.is_hidden.is_(False),
                    models.Task.cron_schedule.isnot(None),
                    models.Task.next_run <= now
                ).all()
                
                for task in tasks:
                    try:
                        # Create execution
                        execution_id = str(uuid.uuid4())
                        execution = models.TaskExecution(
                            execution_id=execution_id,
                            task_id=task.task_id,  # type: ignore
                            status=models.TaskStatusEnum.PENDING,
                            submitted_at=now
                        )
                        
                        db.add(execution)
                        db.flush()
                        
                        # Push to Redis
                        if push_task_to_queue(execution_id):
                            logger.info(f"Created scheduled execution {execution_id} for task {task.task_id}")
                        else:
                            logger.error(f"Failed to queue execution {execution_id}")
                        
                        # Update task's last_run and calculate next_run
                        task.last_run = now  # type: ignore
                        if task.cron_schedule: #type: ignore
                            cron = croniter(task.cron_schedule, now)  # type: ignore
                            task.next_run = cron.get_next(datetime)  # type: ignore
                            logger.debug(f"Next run for task {task.task_id}: {task.next_run}")
                        
                        db.commit()
                        
                    except Exception as e:
                        logger.error(f"Error creating execution for task {task.task_id}: {e}", exc_info=True)
                        db.rollback()
                
                db.close()
                
            except Exception as e:
                logger.error(f"Error in cron evaluator: {e}", exc_info=True)
            
            # Wait before next check
            await asyncio.sleep(orchestrator_settings.cron_check_interval)
    
    async def timeout_monitor(self):
        """
        Periodically check for executions that have exceeded their timeout.
        Marks them as TIMEDOUT.
        """
        logger.info("Timeout monitor started")
        
        while self.running:
            try:
                db = SessionLocal()
                now = datetime.now(UTC)
                
                # Find executions that are in progress and past their timeout
                # Calculate timeout threshold: submitted_at + timeout_seconds < now
                executions = db.query(models.TaskExecution, models.Task).join(
                    models.Task, models.TaskExecution.task_id == models.Task.task_id
                ).filter(
                    models.TaskExecution.status.in_([
                        models.TaskStatusEnum.PENDING,
                        models.TaskStatusEnum.BROADCASTED,
                        models.TaskStatusEnum.IN_PROGRESS
                    ]),
                    models.TaskExecution.is_hidden.is_(False)
                ).all()
                
                for execution, task in executions:
                    # Check if execution has timed out
                    timeout_threshold = execution.submitted_at + timedelta(seconds=task.timeout_seconds)  # type: ignore
                    
                    if now > timeout_threshold:
                        logger.warning(
                            f"Execution {execution.execution_id} timed out "
                            f"(submitted: {execution.submitted_at}, timeout: {task.timeout_seconds}s)"
                        )
                        
                        execution.status = models.TaskStatusEnum.TIMEDOUT  # type: ignore
                        execution.completed_at = now  # type: ignore
                        execution.error_message = f"Execution exceeded timeout of {task.timeout_seconds} seconds"  # type: ignore
                        
                        db.commit()
                
                db.close()
                
            except Exception as e:
                logger.error(f"Error in timeout monitor: {e}", exc_info=True)
            
            # Wait before next check
            await asyncio.sleep(orchestrator_settings.timeout_check_interval)
    
    async def stop(self):
        """Graceful shutdown"""
        logger.info("Stopping Urza Orchestrator Service...")
        self.running = False
        
        if self.cron_task:
            self.cron_task.cancel()
        if self.timeout_task:
            self.timeout_task.cancel()


async def main():
    """Entry point for orchestrator service"""
    setup_orchestrator_logging()
    
    orchestrator = UrzaOrchestrator()
    
    try:
        await orchestrator.start()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
        await orchestrator.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())