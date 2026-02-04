# /urza/db/init_db.py

import logging
import pymysql
from pathlib import Path
from urza.config.settings import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB

logger = logging.getLogger(__name__)


def init_database():
    """
    Initialize database by running schema.sql
    """
    logger.info("Initializing database...")
    
    # Read schema file
    schema_file = Path(__file__).parent / 'schema.sql'
    
    if not schema_file.exists():
        logger.error(f"Schema file not found: {schema_file}")
        raise FileNotFoundError(f"Schema file not found: {schema_file}")
    
    with open(schema_file, 'r') as f:
        schema_sql = f.read()
    
    # Connect and execute
    logger.info(f"Connecting to MySQL: {MYSQL_USER}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}")
    
    connection = pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB,
        charset='utf8mb4'
    )
    
    try:
        with connection.cursor() as cursor:
            # Split on semicolons and execute each statement
            statements = [s.strip() for s in schema_sql.split(';') if s.strip()]
            
            for i, statement in enumerate(statements, 1):
                logger.debug(f"Executing statement {i}/{len(statements)}: {statement[:50]}...")
                cursor.execute(statement)
            
            connection.commit()
            logger.info(f"Database schema created successfully ({len(statements)} statements executed)")
    
    except Exception as e:
        connection.rollback()
        logger.error(f"Failed to initialize database: {str(e)}")
        raise
    
    finally:
        connection.close()


def seed_test_data():
    """
    Seed database with test data for development
    """
    import uuid
    from datetime import datetime, UTC
    
    logger.info("Seeding test data...")
    
    connection = pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    
    try:
        with connection.cursor() as cursor:
            # Create admin role
            cursor.execute("""
                INSERT IGNORE INTO user_roles (name, description, admin, can_create_hidden, can_see_hidden)
                VALUES ('admin', 'Administrator with full access', TRUE, TRUE, TRUE)
            """)
            
            # Create user role
            cursor.execute("""
                INSERT IGNORE INTO user_roles (name, description, admin, can_create_hidden, can_see_hidden)
                VALUES ('user', 'Regular user', FALSE, FALSE, FALSE)
            """)
            
            # Create test admin user (self-referencing for created_by_id)
            admin_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT IGNORE INTO users (user_id, username, role_name, description, created_by_id)
                VALUES (%s, 'admin', 'admin', 'Test admin user', %s)
            """, (admin_id, admin_id))
            
            # Create test regular user
            user_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT IGNORE INTO users (user_id, username, role_name, description, created_by_id)
                VALUES (%s, 'testuser', 'user', 'Test regular user', %s)
            """, (user_id, admin_id))
            
            # Create test platform
            platform_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT IGNORE INTO platforms (id, name, description, os_major_version)
                VALUES (%s, 'Ubuntu Server', 'Ubuntu Linux Server', '22.04')
            """, (platform_id,))
            
            # Create test capabilities
            cap1_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT IGNORE INTO capabilities (id, name, version, description)
                VALUES (%s, 'web-scraping', '1.0.0', 'Selenium-based web scraping')
            """, (cap1_id,))
            
            cap2_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT IGNORE INTO capabilities (id, name, version, description)
                VALUES (%s, 'api-testing', '1.0.0', 'API endpoint testing')
            """, (cap2_id,))
            
            connection.commit()
            logger.info("Test data seeded successfully")
            logger.info(f"Admin ID: {admin_id}")
            logger.info(f"User ID: {user_id}")
            logger.info(f"Platform ID: {platform_id}")
            logger.info(f"Capability IDs: {cap1_id}, {cap2_id}")
    
    except Exception as e:
        connection.rollback()
        logger.error(f"Failed to seed test data: {str(e)}")
        raise
    
    finally:
        connection.close()


def main():
    """
    Main entry point for database initialization
    """
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Initialize schema
        init_database()
        
        # Seed test data
        seed_test_data()
        
        print("\n✅ Database initialized and seeded successfully!")
        
    except Exception as e:
        print(f"\n❌ Database initialization failed: {str(e)}")
        raise


if __name__ == "__main__":
    main()