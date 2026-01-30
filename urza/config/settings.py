# /server/src/config/settings.py
import sys
import os
from pathlib import Path

# Paths
URZA_DIR = Path.home() / '.urza'
SESSION_FILE = URZA_DIR / 'urza_session.session'
CONFIG_FILE = URZA_DIR / 'config.json'
BUILDS_DIR = URZA_DIR / 'builds'
# Environment variables
TG_API_ID=os.getenv('TG_API_ID','')
TG_API_HASH=os.getenv('TG_API_HASH','')


def ensure_directories():
    URZA_DIR.mkdir(parents=True, exist_ok=True)
    BUILDS_DIR.mkdir(exist_ok=True)


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