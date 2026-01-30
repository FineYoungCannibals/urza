# /server/src/utils/telegram_client.py
from urza.config.settings import SESSION_FILE, TG_API_HASH, TG_API_ID
from pathlib import Path
from telethon import TelegramClient
import asyncio
import logging
from rich.console import Console

logger = logging.getLogger(__name__)
console = Console()

class UrzaTGClient:
    """Wrapper around Telethon client for Urza operations"""

    def __init__(self) -> None:
        self.session_file = SESSION_FILE
        self.api_id = TG_API_ID
        self.api_hash = TG_API_HASH
        self.client = None  # Don't create client in __init__
    
    async def connect(self):
        """Async: Connect and authenticate with Telegram"""
        if not self.client:
            self.client = TelegramClient(
                session=str(self.session_file), 
                api_id=int(self.api_id), 
                api_hash=self.api_hash
            )
            await self.client.start()
            
            me = await self.client.get_me()
            console.print(f"[green]✓ Connected as: {me.first_name} {me.last_name} -> @{me.username} [/green]", end='')
        
        return self.client
    
    async def ensure_connected(self):
        """Ensure client is connected before operations"""
        if not self.client or not self.client.is_connected():
            await self.connect()
    
    # ==================== BOT OPERATIONS ====================
    
    async def list_bots(self):
        """Async: Get list of bots from BotFather"""
        await self.ensure_connected()
        
        console.print("[cyan]Fetching bot list from BotFather...[/cyan]")
        
        await self.client.send_message('@BotFather', '/mybots')
        await asyncio.sleep(2)
        
        messages = await self.client.get_messages('@BotFather', limit=1)
        
        for i, msg in enumerate(messages):
            console.print(f"[cyan]Message :{i}[/cyan]")
            console.print(f"Text: {msg.message}")
            if msg.reply_markup:
                for row in msg.reply_markup.rows:
                    for button in row.buttons:
                        console.print(f"Bot: {button.text}")
                        console.print(f"Bot Data: {button.data.decode('utf-8')}")
                        
            console.print()
        return messages
    
    async def create_bot(self, bot_name: str, bot_username: str):
        """Async: Create a new bot via BotFather
        Args:
            bot_name: Display name (e.g., "Recon Bot 5")
            bot_username: Username ending in 'bot' (e.g., "recon_bot_5_bot")
        Returns:
            Tuple of (bot_username, bot_id, token) or None if failed
        """
        await self.ensure_connected()
        console.print(f"[cyan]Creating bot: {bot_name} (@{bot_username})...[/cyan]")
        
        # Step 1a: /newbot
        await self.client.send_message('@BotFather', '/newbot')
        await asyncio.sleep(2)
        
        # Step 1b: Get response with token
        messages = await self.client.get_messages('@BotFather', limit=1)
        msg = messages[0]
        response = msg.message
        # Checking to see if you have made too many
        if 'too many attempts' in response:
            import re
            match = re.search(r'try again in (\d+) seconds', response.lower())
            if match:
                wait_seconds = int(match.group(1))
                wait_hours = wait_seconds/3600
                console.print(f"[red]x Rate Limited! :( Wait {wait_hours:.1f} hours...[/red]")
            else:
                console.print(f"[red]x Rate Limited by TG, check your @Botfather interactions to understand timeframe[/red]")
            return None

        # You aren't rate limited, continue
        # Step 2: Send display name
        await self.client.send_message('@BotFather', bot_name)
        await asyncio.sleep(2)
        
        # Step 3: Send username
        await self.client.send_message('@BotFather', bot_username)
        await asyncio.sleep(2)
        
        # Step 4: Get response with token
        messages = await self.client.get_messages('@BotFather', limit=1)
        msg = messages[0]
        response = msg.message  # <-- Changed from .text to .message

        # Parse token from response
        if 'Use this token' in response:
            lines = response.split('\n')
            token = None
            for line in lines:
                # Look for the token line (format: 1234567890:ABCdef...)
                if line.strip() and ':' in line and 'AAH' in line:
                    token = line.strip()
                    break
            
            if token:
                console.print(f"[green]✓ Bot created successfully![/green]")
                console.print(f"[green]  Name: {bot_name}[/green]")
                console.print(f"[green]  Username: @{bot_username}[/green]")
                console.print(f"[green]  Token: {token}[/green]")
                
                # Extract bot ID from token (first part before the colon)
                bot_id = token.split(':')[0]
                
                return (bot_username, bot_id, token)
    
        # If we didn't find token, show response
        console.print(f"[red]✗ Failed to create bot[/red]")
        console.print(f"[yellow]BotFather response:[/yellow]\n{response}\n")
        return None
    
    async def revoke_bot_token(self, bot_username: str):
        """Async: Revoke a bot's token (useful for cleanup)"""
        await self.ensure_connected()
        
        console.print(f"[yellow]Revoking token for @{bot_username}...[/yellow]")

        # start revocation 
        await self.client.send_message('@BotFather', '/revoke')
        await asyncio.sleep(1)
        messages = await self.client.get_messages('@BotFather', limit=1)

        # BotFather will show list of bots, we send the username
        await self.client.send_message('@BotFather', f'@{bot_username}')
        await asyncio.sleep(2)
        messages = await self.client.get_messages('@BotFather', limit=1)

        msg = messages[0]
        print(msg.message)
        if 'Invalid bot selected' in msg.message:
            console.print(f"[red] Bot not found [/red]")
            return False, ''
        if 'Your token was replaced with a new one' in msg.message:
            import re
            match = re.search(r'HTTP API:\n([^\s]+)$',msg.message,re.MULTILINE)
            console.print(f"[green] Bot token was rotated. New Token: [/green]")
            console.print(f"[yellow]{match.group(1)}[/yellow]")
            return True,match.group(1)
        if 'Sorry, too many attempts.' in msg.message:
            import re
            match = re.search(r'again in (\d+) seconds', msg.message)
            wait = int(match.group(1))/3600
            console.print(f"[red]You got throttled, wait {wait:.1f} hours.[/red]")
            return False,''
        else:
            return False,''
    
    async def disconnect(self):
        """Async: Disconnect from Telegram"""
        if self.client:
            await self.client.disconnect()
            console.print("[yellow]Disconnected from Telegram[/yellow]")
    
    # ==================== SYNC WRAPPERS ====================
    
def setup_sync(self):
    """Sync: Initial setup from CLI"""
    try:
        asyncio.run(self.connect())
    except KeyboardInterrupt:
        console.print("\n[yellow]Setup cancelled[/yellow]")
        sys.exit(0)  # Clean exit on Ctrl+C
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        raise

def list_bots_sync(self):
    """Sync: List bots from CLI"""
    try:
        return asyncio.run(self.list_bots())
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled[/yellow]")
        return None
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        return None

def create_bot_sync(self, bot_name: str, bot_username: str):
    """Sync: Create bot from CLI"""
    try:
        return asyncio.run(self.create_bot(bot_name, bot_username))
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled[/yellow]")
        return None
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        return None