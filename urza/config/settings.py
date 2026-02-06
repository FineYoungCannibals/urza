# /server/src/config/settings.py
import logging
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from pathlib import Path
from typing import Optional


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
    # Redis - Optional
    redis_password: Optional[str] =Field(
        default=None,
        description="Redis user password"
    )
    redis_user: Optional[str] =Field(
        default=None,
        description="Redis user password"
    )
    # Redis - REQUIRED
    redis_host: str = Field(
        ...,
        description="Redis Hostname"
    )
    redis_port: Optional[int] = Field(
        default=6379,
        description="Redis port"
    )
    redis_db: int = Field(
        default=0,
        description="Redis DB Number"
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
    def redis_url(self) -> str:
        """Generate Redis connection URL"""
        if self.redis_user and self.redis_password:
            return f"redis://{self.redis_user}:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        elif self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

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