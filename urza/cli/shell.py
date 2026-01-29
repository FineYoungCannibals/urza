from cmd2 import Cmd,  with_category
import click
import cmd2

from config.display import SHELL_PROMPT, BANNER
import logging
from rich.console import Console

logger = logging.getLogger(__name__)
console = Console()

class UrzaShell(cmd2.Cmd):
    def __init__(self):
        super().__init__(allow_cli_args=False)
        # INIT
        self.prompt = SHELL_PROMPT
        
        # Post INIT
        self.poutput(BANNER)

# =============== SETUP COMMANDS =====================
@with_category("Setup")
def do_setup(self, _):
    """configuring necessary settings for urza"""
    from config.settings import check_setup
