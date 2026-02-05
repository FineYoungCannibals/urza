# /server/src/config/settings.py
import logging
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from pathlib import Path


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables and .env file.
    All fields marked with Field(...) are REQUIRED and must be set in environment.
    """
    base_dir: Path = Path('/app/.urza')
    session_file: Path = Path('/app/.urza/urza_session.session')
    
    # API Settings
    log_level: str = Field(
        default='INFO',
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    api_host: str = Field(
        default="0.0.0.0",
        description="API server host address"
    )
    api_port: int = Field(
        default=8000,
        description="API server port"
    )

    # Bot
    bot_name: str = Field(
        default='thopter',
        description="Name of the bot instance"
    )

    # Telegram - REQUIRED
    tg_api_id: int = Field(
        ...,
        description="Telegram API ID from https://my.telegram.org"
    )
    tg_api_hash: str = Field(
        ...,
        description="Telegram API hash from https://my.telegram.org"
    )
    tg_channel_id: int = Field(
        ...,
        description="Telegram channel ID for bot coordination (negative integer for channels)"
    )
    tg_controller_bot_token: str = Field(
        ...,
        description="Telegram bot token from @BotFather"
    )

    # DigitalOcean / S3-compatible Storage - REQUIRED
    do_token: str = Field(
        ...,
        description="DigitalOcean API token for managing infrastructure"
    )
    do_base_url: str = Field(
        default='https://api.digitalocean.com/v2/',
        description="DigitalOcean API base URL"
    )
    do_bucket_url: str = Field(
        ...,
        description="S3-compatible bucket URL (e.g., https://bucket.region.digitaloceanspaces.com)"
    )

    # MySQL - REQUIRED passwords
    mysql_password: str = Field(
        ...,
        description="MySQL user password"
    )
    mysql_root_password: str = Field(
        ...,
        description="MySQL root password"
    )
    # MySQL - Optional with defaults
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
    mysql_db: str = Field(
        default='urza_db',
        description="MySQL database name"
    )

    @field_validator('log_level')
    @classmethod
    def get_log_level(cls, v: str) -> str:
        """Validate log level"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        level_upper = v.upper()
        if level_upper in valid_levels:
            return level_upper
        else:
            print(f"WARNING: Invalid log level '{v}', defaulting to INFO")
            return 'INFO'

    @property
    def database_url(self) -> str:
        """Generate async SQLAlchemy database URL"""
        return (
            f"mysql+aiomysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}"
        )

    @property
    def database_url_sync(self) -> str:
        """Generate synchronous SQLAlchemy database URL"""
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}"
        )
        
    class Config:
        env_file = ".env"
        case_sensitive = False


# Create settings instance - reads from environment variables and .env file
settings = Settings() # type: ignore[call-args]

def setup_logging():
    """
    Configure logging globally.
    Call once at application startup.
    """
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        force=True
    )
    
    # Quiet noisy third-party loggers
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
   
    # Return a logger for the application
    logger = logging.getLogger("urza")
    logger.info(f"Logging configured at {settings.log_level} level")
    return logger