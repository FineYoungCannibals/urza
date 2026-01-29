# server/test_telegram.py
import asyncio
import sys
from pathlib import Path
import os


# Add to path
sys.path.insert(0, str(Path(__file__).parent.parent))

print(sys.path)
from urza.config.settings import SESSION_FILE, TG_API_HASH, TG_API_ID
print(f"Session path {SESSION_FILE}")


print(os.getenv('TG_API_HASH'))
print(os.getenv('TG_API_ID'))

from urza.core.telegram_client import UrzaTGClient

async def test():
    print("Creating client...")
    client = UrzaTGClient()
    
    print("Connecting...")
    await client.connect()
    
    print("Creating bot")
    result = await client.create_bot('thopter5', 'thopter5_bot')
    if result:
        print(result)

    print("\nListing bots...")
    await client.list_bots()
    
    print("\nDisconnecting...")
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(test())