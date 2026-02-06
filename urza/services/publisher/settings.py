# urza/services/publisher/settings.py

"""
Configuration for urza_publisher service.

This service reads TaskExecutions from Redis queue and broadcasts them to Telegram channel.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path
from typing import Optional


class PublisherSettings(BaseSettings):
    """
    Settings for urza_publisher service.
    
    Loads from environment variables or .env file.
    Can be run independently from API and other services.
    """
    
    # Telegram Configuration
    tg_api_id: str = Field(
        ...,
        description="Telegram API ID"
    )
    tg_api_hash: str = Field(
        ...,
        description="Telegram API Hash"
    )
    tg_channel_id: str = Field(
        ...,
        description="Telegram channel ID to broadcast tasks"
    )
    tg_controller_bot_token: str = Field(
        ...,
        description="Telegram bot token with message write access to channel"
    )
    
    # Database Configuration
    mysql_host: str = Field(
        default='localhost',
        description="MySQL server host"
    )
    mysql_port: int = Field(
        default=3306,
        description="MySQL server port"
    )
    mysql_user: str = Field(
        default='urza',
        description="MySQL username"
    )
    mysql_password: str = Field(
        ...,
        description="MySQL user password"
    )
    mysql_db: str = Field(
        default='urza_db',
        description="MySQL database name"
    )
    
    # Redis Configuration
    redis_host: str = Field(
        ...,
        description="Redis hostname"
    )
    redis_port: int = Field(
        default=6379,
        description="Redis port"
    )
    redis_password: Optional[str] = Field(
        default=None,
        description="Redis password (optional)"
    )
    redis_user: Optional[str] = Field(
        default=None,
        description="Redis username (optional)"
    )
    redis_db: int = Field(
        default=0,
        description="Redis DB number"
    )
    
    # Publisher Configuration
    poll_interval: int = Field(
        default=5,
        description="How often to check Redis queue for new tasks (seconds)"
    )
    log_level: str = Field(
        default='INFO',
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    service_name: str = Field(
        default='urza_publisher',
        description="Service identifier for logging"
    )
    
    @property
    def database_url_sync(self) -> str:
        """Generate synchronous SQLAlchemy database URL"""
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}"
        )
    
    @property
    def redis_url(self) -> str:
        """Generate Redis connection URL"""
        if self.redis_user and self.redis_password:
            return f"redis://{self.redis_user}:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        elif self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = 'allow'


# Singleton instance
publisher_settings = PublisherSettings()  # type: ignore


def setup_publisher_logging():
    """
    Configure logging for publisher service.
    Call once at service startup.
    """
    import logging
    
    logging.basicConfig(
        level=getattr(logging, publisher_settings.log_level),
        format=f'%(asctime)s - {publisher_settings.service_name} - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        force=True
    )
    
    # Quiet noisy third-party loggers
    logging.getLogger("telethon").setLevel(logging.WARNING)
    logging.getLogger("pymysql").setLevel(logging.WARNING)
    
    logger = logging.getLogger(publisher_settings.service_name)
    logger.info(f"Logging configured at {publisher_settings.log_level} level")
    logger.info(f"Poll interval: {publisher_settings.poll_interval}s")
    logger.info(f"Channel: {publisher_settings.tg_channel_id}")
    logger.info(f"Database: {publisher_settings.mysql_host}:{publisher_settings.mysql_port}/{publisher_settings.mysql_db}")
    
    return logger