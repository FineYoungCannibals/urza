# /server/src/utils/telegram_client.py
from urza.config.settings import settings
from telethon import TelegramClient
from telethon.tl.functions.channels import EditAdminRequest, EditBannedRequest
from telethon.tl.types import ChatAdminRights, ChatBannedRights
import asyncio
import logging
from rich.console import Console

logger = logging.getLogger(__name__)
console = Console()

class UrzaTGClient:
    """Wrapper around Telethon client for Urza operations"""

    def __init__(self) -> None:
        self.session_file = settings.session_file
        self.api_id = settings.tg_api_id
        self.api_hash = settings.tg_api_hash
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
            console.print(f"[green]✓ Connected as: {me.first_name} {me.last_name} -> @{me.username} [/green]\n", end='')
        
        return self.client
    
    async def ensure_connected(self):
        """Ensure client is connected before operations"""
        if not self.client or not self.client.is_connected():
            await self.connect()
    
    # ==================== BOT OPERATIONS ====================
    async def delete_bot(self, bot_username):
        """Async: Delete a bot via BotFather"""
        import re

        await self.ensure_connected()

        await self.client.send_message('@BotFather', '/deletebot')

        await asyncio.sleep(3)

        await self.client.send_message('@BotFather',f'@{bot_username}')

        messages = await self.client.get_messages('@BotFather', limit=1)
        msg = messages[0]
        await asyncio.sleep(3)

        if f'OK, you selected @{bot_username}. Are you sure?' in msg.message:
            match = re.search(r"Send '(?P<confirmation>[^\']+?)'", msg.message, re.MULTILINE)
            await asyncio.sleep(3)
            if match:
                print(match.group('confirmation'))
                await self.client.send_message('@BotFather',f'{match.group('confirmation')}')
                return True
            else:
                print('error')
                return False

    
    async def list_bots(self):
        """Async: Get list of bots from BotFather"""
        await self.ensure_connected()
        
        console.print("[cyan]Fetching bot list from BotFather...[/cyan]\n")
        
        await self.client.send_message('@BotFather', '/mybots')
        await asyncio.sleep(2)
        
        messages = await self.client.get_messages('@BotFather', limit=1)
        
        for i, msg in enumerate(messages):
            console.print(f"[cyan]Message :{i}[/cyan]\n")
            console.print(f"Text: {msg.message}\n")
            if msg.reply_markup:
                for row in msg.reply_markup.rows:
                    for button in row.buttons:
                        console.print(f"Bot: {button.text}\n")
                        console.print(f"Bot Data: {button.data.decode('utf-8')}\n")
                        
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
        console.print(f"[cyan]Creating bot: {bot_name} (@{bot_username})...[/cyan]\n")
        
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
                console.print(f"[red]x Rate Limited! :( Wait {wait_hours:.1f} hours...[/red]\n")
            else:
                console.print(f"[red]x Rate Limited by TG, check your @Botfather interactions to understand timeframe[/red]\n")
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
        response = msg.message


        # Parse token from response
        if 'Use this token' in response:
            import re
            match = re.search(r'Use this token to access the HTTP API:\s(?P<token>(?P<id>\d+):(?P<authkey>[^\s]+?))\s', response, re.MULTILINE)
            if match:
                console.print(f"[green]✓ Bot created successfully![/green]\n")
                console.print(f"[green]  Name: {bot_name} ID: {match.group('id')}[/green]\n")
                console.print(f"[green]  Username: @{bot_username}[/green]\n")
                console.print(f"[green]  Token: {match.group('token')}[/green]\n")
                return (bot_username, match.group('id'), match.group('token'))
            
            else:
                console.print(f"[green]✓ Bot created successfully![/green]\n")
                console.print(f"[yellow] Error parsing token from response.[/yellow]\n")
                console.print(f"[green] Username: @{bot_username}[/green]\n")
                console.print(f"[yellow] ID Not Parsed\n[/yellow]")
                console.print(f"[yellow] Token Not Parsed[/yellow]")
                return (bot_username, '','') 
                # Extract bot ID from token (first part before the colon)
                
    
        # If we didn't find token, show response
        console.print(f"[red]✗ Failed to create bot[/red]\n")
        console.print(f"[yellow]BotFather response:[/yellow]\n{response}\n")
        return (None,None,None)
    
    async def revoke_bot_token(self, bot_username: str):
        """Async: Revoke a bot's token (useful for cleanup)"""
        await self.ensure_connected()
        
        console.print(f"[yellow]Revoking token for @{bot_username}...[/yellow]\n")

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
            console.print(f"[red] Bot not found [/red]\n")
            return False, ''
        if 'Your token was replaced with a new one' in msg.message:
            import re
            match = re.search(r'HTTP API:\n([^\s]+)$',msg.message,re.MULTILINE)
            console.print(f"[green] Bot token was rotated. New Token: [/green]\n")
            console.print(f"[yellow]{match.group(1)}[/yellow]\n")
            return True,match.group(1)
        if 'Sorry, too many attempts.' in msg.message:
            import re
            match = re.search(r'again in (\d+) seconds', msg.message)
            wait = int(match.group(1))/3600
            console.print(f"[red]You got throttled, wait {wait:.1f} hours.[/red]\n")
            return False,''
        else:
            return False,''
    
    async def disconnect(self):
        """Async: Disconnect from Telegram"""
        if self.client:
            await self.client.disconnect()
            console.print("[yellow]Disconnected from Telegram[/yellow]\n")
    # ==================== CHANNEL OPERATIONS ===============

    async def ban_from_channel(self, bot_username):
        channel = await self.client.get_entity(settings.tg_channel_id)
        bot = await self.client.get_entity(bot_username)

        await self.client(EditBannedRequest(
            channel=channel,
            participant=bot,
            banned_rights=ChatBannedRights(
                until_date=None, # Permaban lawl
                view_messages=True
            )
        ))
        console.print(f"[green]Removed bot {bot_username} from channel.[/green]")
        return True

    async def add_bot_to_channel(self,bot_username):
        channel = await self.client.get_entity(int(settings.tg_channel_id))

        bot = await self.client.get_entity(bot_username)

        admin_rights = ChatAdminRights(
            post_messages=True,
            edit_messages=False,
            delete_messages=False,
            ban_users=False,
            invite_users=False,
            pin_messages=False,
            anonymous=False,
            manage_topics=False,
            post_stories=False,
            edit_stories=False,
            delete_stories=False
        )

        await self.client(EditAdminRequest(
            channel=channel,
            user_id=bot,
            admin_rights=admin_rights,
            rank='Bot'
        ))

        print(f"Added {bot_username} as limited admin to channel.")
        return True

     
    # ==================== SYNC WRAPPERS ====================
    
    def setup_sync(self):
        """Sync: Initial setup from CLI"""
        try:
            asyncio.run(self.connect())
        except KeyboardInterrupt:
            console.print("\n[yellow]Setup cancelled[/yellow]\n")
        except Exception as e:
            console.print(f"[red]✗ Error: {e}[/red]")

    
    def list_bots_sync(self):
        """Sync: List bots from CLI"""
        try:
            return asyncio.run(self.list_bots())
        except KeyboardInterrupt:
            console.print("\n[yellow]Operation cancelled[/yellow]\n")
            return None
        except Exception as e:
            console.print(f"[red]✗ Error: {e}[/red]")
            return None
    
    def create_bot_sync(self, bot_name: str, bot_username: str):
        """Sync: Create bot from CLI"""
        try:
            return asyncio.run(self.create_bot(bot_name, bot_username))
        except KeyboardInterrupt:
            console.print("\n[yellow]Operation cancelled[/yellow]\n")
            return None
        except Exception as e:
            console.print(f"[red]✗ Error: {e}[/red]\n")
            return None