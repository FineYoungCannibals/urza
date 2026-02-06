# Telegram Monitor service - in charge of:
# handling bot claims, checkins, and results


# urza/services/bot/main.py

import asyncio
import logging
from telethon import TelegramClient, events

from urza.services.bot.settings import bot_settings, setup_bot_logging
from urza.db.session import SessionLocal
from urza.services.bot import protocol

logger = logging.getLogger(__name__)


class UrzaBotService:
    """
    Monitors Telegram channel for bot worker messages using controller bot.
    Updates database with task execution status and results.
    """
    
    def __init__(self):
        self.client = TelegramClient(
            'urza_bot_session',
            int(bot_settings.tg_api_id),
            bot_settings.tg_api_hash
        )
        self.bot_token = bot_settings.tg_controller_bot_token
        self.channel_id = int(bot_settings.tg_channel_id)
        self.running = False
        
    async def start(self):
        """Initialize and start the bot service"""
        logger.info("Starting Urza Bot Service...")
        
        await self.client.start(bot_token=self.bot_token)
        
        me = await self.client.get_me()
        logger.info(f"Connected as bot: @{me.username}")
        
        self.register_handlers()
        
        self.running = True
        logger.info(f"Monitoring channel {self.channel_id} for bot messages...")
        
        await self.client.run_until_disconnected()
    
    def register_handlers(self):
        """Register Telethon event handlers for bot commands"""
        
        @self.client.on(events.NewMessage(
            chats=self.channel_id,
            pattern=r'^/claim'
        ))
        async def on_claim(event):
            await protocol.handle_claim(event, SessionLocal)
        
        @self.client.on(events.NewMessage(
            chats=self.channel_id,
            pattern=r'^/status'
        ))
        async def on_status(event):
            await protocol.handle_status(event, SessionLocal)
        
        @self.client.on(events.NewMessage(
            chats=self.channel_id,
            pattern=r'^/complete|^/failed'
        ))
        async def on_result(event):
            await protocol.handle_result(event, SessionLocal)

        @self.client.on(events.NewMessage(
            chats=self.channel_id,
            pattern=r'^/checkin'
        ))
        async def on_checkin(event):
            await protocol.handle_checkin(event, SessionLocal)
    
    # In the register_handlers method, add:

    
    async def stop(self):
        """Graceful shutdown"""
        logger.info("Stopping Urza Bot Service...")
        self.running = False
        await self.client.disconnect()


async def main():
    """Entry point for urza_bot service"""
    setup_bot_logging()
    
    service = UrzaBotService()
    
    try:
        await service.start()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
        await service.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())