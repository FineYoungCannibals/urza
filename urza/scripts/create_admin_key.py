"""
Bootstrap script to create an initial admin API key
Run once: python -m urza.scripts.create_admin_key

This script is idempotent - it checks if admin already has a key
and only creates one if none exist.
"""

import sys
import logging
from urza.db.session import SessionLocal
from urza.db import models
from urza.api.auth import generate_api_key
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_admin_key():
    """Create an API key for the admin user if one doesn't exist"""
    db = SessionLocal()
    
    try:
        # Get admin user
        admin = db.query(models.User).filter_by(username="admin").first()
        if not admin:
            logger.error("❌ Admin user not found. Run seed script first!")
            logger.error("   python -m urza.db.seed")
            sys.exit(1)
        
        # Check if admin already has any active API keys
        existing_keys = db.query(models.APIKey).filter_by(
            user_id=admin.user_id,
            is_active=True,
            is_hidden=False
        ).count()
        
        if existing_keys > 0:
            logger.info("ℹ️  Admin already has an API key. Skipping creation.")
            logger.info("   Use /api-keys endpoint to create additional keys.")
            return
        
        # Generate key
        raw_key, hashed_key = generate_api_key()
        
        # Create API key
        key_id = str(uuid.uuid4())
        api_key = models.APIKey(
            id=key_id,
            name="Bootstrap Admin Key",
            hashed_key=hashed_key,
            user_id=admin.user_id,
            created_by_id=admin.user_id,
            is_active=True,
            is_hidden=False
        )
        
        db.add(api_key)
        db.commit()
        
        # Print the key prominently
        print("\n" + "="*70)
        print("✅ ADMIN API KEY CREATED SUCCESSFULLY!")
        print("="*70)
        print(f"\n🔑 API Key: {raw_key}")
        print("\n⚠️  IMPORTANT: SAVE THIS KEY NOW!")
        print("   This key will NOT be shown again.")
        print("   You will need it to authenticate API requests.")
        print("\n📝 Usage Example:")
        print(f'   curl -H "X-API-Key: {raw_key}" \\')
        print("        http://localhost:8000/users/")
        print("\n💡 To create additional keys:")
        print("   POST /api-keys (requires this key for authentication)")
        print("="*70 + "\n")
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to create admin key: {e}")
        sys.exit(1)
    
    finally:
        db.close()

if __name__ == "__main__":
    create_admin_key()