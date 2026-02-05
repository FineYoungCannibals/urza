"""
Seed script for development data
Run with: python -m urza.db.seed
"""

import uuid
import logging
from datetime import datetime, UTC
from urza.db.session import SessionLocal
from urza.db import models

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
                can_create_hidden=True,
                can_see_hidden=True
            )
            user_role = models.UserRole(
                name="user",
                description="Regular user",
                admin=False,
                can_create_hidden=False,
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
        
        # 4. Create Platforms
        logger.info("Creating platforms...")
        
        existing_ubuntu = db.query(models.Platform).filter_by(name="Ubuntu Server 22.04").first()
        if existing_ubuntu:
            logger.info("Platforms already exist, skipping")
            ubuntu_id = existing_ubuntu.id
        else:
            ubuntu_id = str(uuid.uuid4())
            debian_id = str(uuid.uuid4())
            
            ubuntu_platform = models.Platform(
                id=ubuntu_id,
                name="Ubuntu Server 22.04",
                description="Ubuntu Linux Server",
                os_major_version="22.04"
            )
            debian_platform = models.Platform(
                id=debian_id,
                name="Debian 12",
                description="Debian Linux",
                os_major_version="12"
            )
            db.add(ubuntu_platform)
            db.add(debian_platform)
            db.commit()
            logger.info(f"✅ Platforms created: Ubuntu={ubuntu_id}, Debian={debian_id}")
        
        # 5. Create Capabilities
        logger.info("Creating capabilities...")
        
        existing_scraping = db.query(models.Capability).filter_by(name="web-scraping").first()
        if existing_scraping:
            logger.info("Capabilities already exist, skipping")
            scraping_id = existing_scraping.id
        else:
            scraping_id = str(uuid.uuid4())
            api_id = str(uuid.uuid4())
            osint_id = str(uuid.uuid4())
            
            scraping_cap = models.Capability(
                id=scraping_id,
                name="web-scraping",
                version="1.0.0",
                description="Selenium-based web scraping with RowdyBottyPiper"
            )
            api_cap = models.Capability(
                id=api_id,
                name="api-testing",
                version="1.0.0",
                description="RESTful API endpoint testing"
            )
            osint_cap = models.Capability(
                id=osint_id,
                name="osint-collection",
                version="1.0.0",
                description="Open source intelligence gathering"
            )
            db.add(scraping_cap)
            db.add(api_cap)
            db.add(osint_cap)
            db.commit()
            logger.info(f"✅ Capabilities created: scraping={scraping_id}, api={api_id}, osint={osint_id}")
        
        logger.info("\n" + "="*60)
        logger.info("✅ Database seeded successfully!")
        logger.info("="*60)
        logger.info(f"\n📝 Test Credentials:")
        logger.info(f"   Admin User ID: {admin_id}")
        logger.info(f"   Test User ID: {user_id}")
        logger.info(f"   Ubuntu Platform ID: {ubuntu_id}")
        logger.info(f"   Web Scraping Capability ID: {scraping_id}")
        logger.info("\n💡 You can now test the API endpoints!")
        logger.info("="*60 + "\n")
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Seeding failed: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()