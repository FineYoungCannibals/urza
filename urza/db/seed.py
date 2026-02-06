"""
Seed script for development data
Run with: python -m urza.db.seed
"""

import uuid
import logging
from datetime import datetime, UTC
from urza.db.session import SessionLocal
from urza.db import models
from urza.api.auth import generate_api_key

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def seed_data():
    """Seed the database with test data"""
    db = SessionLocal()
    
    try:
        logger.info("🌱 Starting database seed...")
        
        # 1. Create Roles
        logger.info("Creating roles...")
        
        # Check if roles already exist
        existing_admin = db.query(models.UserRole).filter_by(name="admin").first()
        if existing_admin:
            logger.info("Roles already exist, skipping role creation")
        else:
            admin_role = models.UserRole(
                name="admin",
                description="Administrator with full access",
                admin=True,
                can_see_hidden=True
            )
            user_role = models.UserRole(
                name="user",
                description="Regular user",
                admin=False,
                can_see_hidden=False
            )
            db.add(admin_role)
            db.add(user_role)
            db.commit()
            logger.info("✅ Roles created")
        
        # 2. Create Admin User (self-referencing)
        logger.info("Creating admin user...")
        
        existing_admin_user = db.query(models.User).filter_by(username="admin").first()
        if existing_admin_user:
            logger.info("Admin user already exists, skipping")
            admin_id = existing_admin_user.user_id
        else:
            admin_id = str(uuid.uuid4())
            admin_user = models.User(
                user_id=admin_id,
                username="admin",
                role_name="admin",
                description="System administrator",
                created_by_id=admin_id,  # Self-created
                is_active=True,
                is_hidden=False
            )
            db.add(admin_user)
            db.commit()
            logger.info(f"✅ Admin user created: {admin_id}")
        
        # 3. Create Regular User
        logger.info("Creating test user...")
        
        existing_test_user = db.query(models.User).filter_by(username="testuser").first()
        if existing_test_user:
            logger.info("Test user already exists, skipping")
            user_id = existing_test_user.user_id
        else:
            user_id = str(uuid.uuid4())
            test_user = models.User(
                user_id=user_id,
                username="testuser",
                role_name="user",
                description="Test user for development",
                created_by_id=admin_id,
                is_active=True,
                is_hidden=False
            )
            db.add(test_user)
            db.commit()
            logger.info(f"✅ Test user created: {user_id}")
        
        # 4. Create API Keys for testing
        logger.info("Creating API keys...")
        
        existing_admin_key = db.query(models.APIKey).filter_by(
            user_id=admin_id,
            name="admin-dev-key"
        ).first()
        
        if existing_admin_key:
            logger.info("API keys already exist, skipping")
        else:
            # Admin API key
            raw_admin_key, hashed_admin_key = generate_api_key()
            admin_api_key = models.APIKey(
                id=str(uuid.uuid4()),
                name="admin-dev-key",
                hashed_key=hashed_admin_key,
                user_id=admin_id,
                created_by_id=admin_id,
                is_active=True,
                is_hidden=False
            )
            
            # Test user API key
            raw_user_key, hashed_user_key = generate_api_key()
            user_api_key = models.APIKey(
                id=str(uuid.uuid4()),
                name="testuser-dev-key",
                hashed_key=hashed_user_key,
                user_id=user_id,
                created_by_id=admin_id,
                is_active=True,
                is_hidden=False
            )
            
            db.add(admin_api_key)
            db.add(user_api_key)
            db.commit()
            
            logger.info(f"✅ API keys created")
            logger.info(f"   Admin API Key: {raw_admin_key}")
            logger.info(f"   Test User API Key: {raw_user_key}")
        
        logger.info("\n" + "="*60)
        logger.info("✅ Database seeded successfully!")
        logger.info("="*60)
        logger.info(f"\n📝 Test Credentials:")
        logger.info(f"   Admin User ID: {admin_id}")
        logger.info(f"   Test User ID: {user_id}")
        logger.info("\n💡 You can now test the API endpoints!")
        logger.info("   Use the X-API-Key header with one of the keys above")
        logger.info("="*60 + "\n")
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Seeding failed: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()