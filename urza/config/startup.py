from pathlib import Path
from urza.config.settings import settings


def ensure_directories():
    settings.base_dir.mkdir(parents=True, exist_ok=True)

def check_setup():
    """Check if session file for TG has been configured """
    status = False
    if settings.session_file.exists():
        status = True
    return status

def setup_urza():
    ensure_directories()
    check_setup()
    return 