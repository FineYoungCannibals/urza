# urza/services/orchestrator/settings.py

"""
Configuration for urza_orchestrator service.

This service runs independently and handles:
- Cron schedule evaluation (creates TaskExecutions when scheduled)
- Timeout monitoring (marks executions as TIMEDOUT)
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class OrchestratorSettings(BaseSettings):
    """
    Settings for urza_orchestrator service.
    
    Loads from environment variables or .env file.
    Can be run independently from API and bot services.
    """
    
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
    redis_password: str = Field( #type: ignore
        default=None,
        description="Redis password (optional)"
    )
    redis_user: str = Field( #type: ignore
        default=None,
        description="Redis username (optional)"
    )
    redis_db: int = Field(
        default=0,
        description="Redis DB number"
    )
    
    # Orchestrator Configuration
    cron_check_interval: int = Field(
        default=60,
        description="How often to check for scheduled tasks (seconds)"
    )
    timeout_check_interval: int = Field(
        default=300,
        description="How often to check for timed out executions (seconds)"
    )
    log_level: str = Field(
        default='INFO',
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    service_name: str = Field(
        default='urza_orchestrator',
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
orchestrator_settings = OrchestratorSettings()  # type: ignore


def setup_orchestrator_logging():
    """
    Configure logging for orchestrator service.
    Call once at service startup.
    """
    import logging
    
    logging.basicConfig( #
        level=getattr(logging, orchestrator_settings.log_level),
        format=f'%(asctime)s - {orchestrator_settings.service_name} - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        force=True
    )
    
    # Quiet noisy third-party loggers
    logging.getLogger("pymysql").setLevel(logging.WARNING)
    
    logger = logging.getLogger(orchestrator_settings.service_name)
    logger.info(f"Logging configured at {orchestrator_settings.log_level} level")
    logger.info(f"Cron check interval: {orchestrator_settings.cron_check_interval}s")
    logger.info(f"Timeout check interval: {orchestrator_settings.timeout_check_interval}s")
    logger.info(f"Database: {orchestrator_settings.mysql_host}:{orchestrator_settings.mysql_port}/{orchestrator_settings.mysql_db}")
    
    return logger