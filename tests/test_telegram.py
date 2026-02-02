# server/test_telegram.py
import asyncio
import sys
from pathlib import Path
import os
import random


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
    
    #newbot = 'thopter'+str(random.randint(100,1000000))
    #botname = newbot+'_bot'
    #print("Creating bot")
    #result = await client.create_bot(newbot, botname)
    #if result:
    #    print(result)

    print("\nListing bots...")
    await client.list_bots()


    #print("\nPermabanning a bot")
    #await client.ban_from_channel(bot_username='thopter374296_bot')

    print("Deleting bot")
    await client.delete_bot(bot_username='thopter374296_bot')

    #print(f"Adding {botname} bot to channel")
    #await client.add_bot_to_channel(bot_username='@'+botname)

    #print("\nRevoking bots...")
    #await client.revoke_bot_token('thopter3_bot')
    
    print("\nDisconnecting...")
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(test())