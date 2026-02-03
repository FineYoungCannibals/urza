# /server/src/config/settings.py
import sys
import os
from pathlib import Path
import logging
from pydantic_settings import BaseSettings
from pydantic import field_validator


# BOTNAME
BOT = os.getenv('BOT_NAME','thopter')
# Paths
URZA_DIR = Path.home() / '.urza'
SESSION_FILE = URZA_DIR / 'urza_session.session'

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
# === == === == = == == = = == = = == == = == === === ====

class Settings(BaseSettings):
    log_level: str = 'INFO'
    api_host: str = "0.0.0.0"
    api_port: int = 8000

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

def ensure_directories():
    URZA_DIR.mkdir(parents=True, exist_ok=True)

def check_setup():
    """Check if session file for TG has been configured """
    status = {}
    if not SESSION_FILE.exists():
        print("Urza must be run from the cli.py component to register a user session.")
        status['urza_session'] = False
    else:
        status['urza_session'] = True
    if not os.getenv('DO_TOKEN'):
        print("DO_TOKEN environment variable must be set in the Urza docker container.")
        status['urza_do_token'] = False 
    else:
        status['urza_do_token'] = True
    if not DO_BUCKET_TOKEN or not DO_BUCKET_TOKEN_ID or not DO_BUCKET_URL or not DO_BUCKET_NAME:
        print("DO bucket environment variables need to be set, check the .env_template and check DO BUCKET section for env vars to instantiate")
        status['urza_do_bucket_config']=False
    else:
        status['urza_do_bucket_config'] = True
    if not os.getenv('TG_CONTROLLER_BOT_TOKEN'):
        print('TG_CONTROLLER_BOT_TOKEN environment variable must be set in the Urza docker container.')
        status['urza_tg_controller_bot_token'] = False
    else:
        status['urza_tg_controller_bot_token'] = True
    return status


def is_ready():
    return all(check_setup().values())


def setup_urza():
    ensure_directories()
    is_ready()
    return 