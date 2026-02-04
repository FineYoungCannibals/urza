# /server/src/config/settings.py
import sys
import os
from pathlib import Path
import logging
from pydantic_settings import BaseSettings
from pydantic import field_validator

# BOTNAME
BOT = os.getenv('BOT_NAME','thopter')

# TG Specific
TG_API_ID=os.getenv('TG_API_ID','')
TG_API_HASH=os.getenv('TG_API_HASH','')
TG_CHANNEL_ID=int(os.getenv('TG_CHANNEL_ID','0'))
# DO Specific
DO_TOKEN=os.getenv('DO_TOKEN','')
DO_BASE_URL='https://api.digitalocean.com/v2/'
DO_BUCKET_TOKEN=os.getenv('DO_BUCKET_TOKEN')
DO_BUCKET_TOKEN_ID=os.getenv('DO_BUCKET_TOKEN_ID')
DO_BUCKET_URL=os.getenv('DO_BUCKET_URL')
DO_BUCKET_NAME=os.getenv('DO_BUCKET_NAME')
# Database specific
MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
MYSQL_PORT = int(os.getenv('MYSQL_PORT', '3306'))
MYSQL_USER = os.getenv('MYSQL_USER', 'urza')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
MYSQL_DB = os.getenv('MYSQL_DB', 'urza_db')

class Settings(BaseSettings):
    # API Settings
    log_level: str = 'INFO'
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # bot
    bot_name: str = 'thopter'

    # Telegram
    tg_api_id: str = ''
    tg_api_hash: str = ''
    tg_channel_id: str = ''
    tg_controller_bot_token: str = ''

    # DO settings
    do_token: str = ''
    do_bucket_token: str | None = None
    do_bucket_token_id: str | None = None
    do_bucket_url: str | None = None
    do_bucket_name: str | None = None


    # MySQL
    mysql_host: str = 'localhost'
    mysql_port: int = 3306
    mysql_user: str = 'urza'
    mysql_password: str = ''
    mysql_db: str = 'urza_db'
    mysql_root_password: str = 'changemeplease'
    

    @field_validator('log_level')
    @classmethod
    def get_log_level(cls, v:str) -> str:
        """ validate log level """
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        level_upper = v.upper()
        if level_upper in valid_levels:
            return level_upper
        else:
            print(f"WARNING: Invalid log level '{v}, defaulting to INFO")
            return 'INFO'
        
    class Config:
        env_file = ".env"
        case_sensitive = False

# create settings instance
settings = Settings()

def setup_logging():
    """
    Configure logging globally.
    Call once at application startup.
    """
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        force=True  # Reconfigure if already configured
    )
    
    # Quiet noisy third-party loggers
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
   
    # Return a logger for the application
    logger = logging.getLogger("urza")  # Fixed name!
    logger.info(f"Logging configured at {settings.log_level} level")
    return logger
