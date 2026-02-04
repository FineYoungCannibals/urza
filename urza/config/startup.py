from pathlib import Path

# Paths
URZA_DIR = Path('/app') / '.urza'
SESSION_FILE = URZA_DIR / 'urza_session.session'

def ensure_directories():
    URZA_DIR.mkdir(parents=True, exist_ok=True)

def check_setup():
    """Check if session file for TG has been configured """
    status = False
    if SESSION_FILE.exists():
        status = True
    return status

def setup_urza():
    ensure_directories()
    check_setup()
    return 