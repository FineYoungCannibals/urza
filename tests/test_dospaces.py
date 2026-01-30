"""
Test script for DigitalOcean Agent
"""
import sys
from pathlib import Path
import random

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from urza.core.spaces_client import DOAgent

def test_connection():
    print("\nTesting DO API connection...")
    agent = DOAgent()
    result = agent.test_connection()
    print(f"Connection result: {result}")

def test_list_keys():
    print("\nListing Spaces keys...")
    agent = DOAgent()
    keys = agent.list_keys()
    print(f"Keys: {keys}")

def test_create_keys():
    print("\nCreating Spaces keys...")
    agent = DOAgent()
    result = agent.create_spaces_keys(f'thopter{str(int(random.random()))}')
    print(f"Create result: {result}")

def test_revoke_keys():
    print("\nRevoking Spaces keys...")
    agent = DOAgent()
    result = agent.revoke_spaces_keys("test_key_123")
    print(f"Revoke result: {result}")

if __name__ == '__main__':
    print("Testing DOAgent...")
    
    test_connection()
    test_list_keys()
    test_create_keys()
    # test_revoke_keys()
    
    print("\nDone!")