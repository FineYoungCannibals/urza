# urza/services/bot/config.py

"""
Configuration for urza_bot service - the Telegram monitor that watches for bot responses.

This service runs independently from the API and only needs:
- Telegram credentials (bot token)
- Database connection (to update task executions)
"""

from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict, field_validator
import logging


class BotServiceSettings(BaseSettings):
    """
    Settings for urza_bot service.
    
    Loads from environment variables or .env file.
    Can be run independently from main API.
    """
    
    # Telegram Bot Authentication
    tg_api_id: str = Field(
        ...,
        description="Telegram API ID for Telethon client"
    )
    tg_api_hash: str = Field(
        ...,
        description="Telegram API Hash for Telethon client"
    )
    tg_controller_bot_token: str = Field(
        ...,
        description="Bot token for controller bot that monitors channel for worker responses"
    )
    tg_channel_id: str = Field(
        ...,
        description="Telegram channel ID to monitor (format: -1001234567890)"
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
    
    # Service Configuration
    log_level: str = Field(
        default='INFO',
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    service_name: str = Field(
        default='urza_bot',
        description="Service identifier for logging"
    )
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        level_upper = v.upper()
        if level_upper in valid_levels:
            return level_upper
        else:
            print(f"WARNING: Invalid log level '{v}', defaulting to INFO")
            return 'INFO'
    
    @property
    def database_url_sync(self) -> str:
        """Generate synchronous SQLAlchemy database URL"""
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}"
        )
    
    class Config:
        env_file=".env",
        case_sensitive=False,
        extra='allow'


# Singleton instance
bot_settings = BotServiceSettings()  # type: ignore


def setup_bot_logging():
    """
    Configure logging for bot service.
    Call once at service startup.
    """
    logging.basicConfig(
        level=getattr(logging, bot_settings.log_level),
        format=f'%(asctime)s - {bot_settings.service_name} - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        force=True
    )
    
    # Quiet noisy third-party loggers
    logging.getLogger("telethon").setLevel(logging.WARNING)
    logging.getLogger("pymysql").setLevel(logging.WARNING)
    
    logger = logging.getLogger(bot_settings.service_name)
    logger.info(f"Logging configured at {bot_settings.log_level} level")
    logger.info(f"Monitoring channel: {bot_settings.tg_channel_id}")
    logger.info(f"Database: {bot_settings.mysql_host}:{bot_settings.mysql_port}/{bot_settings.mysql_db}")
    
    return logger