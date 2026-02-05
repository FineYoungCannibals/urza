"""
Database session management for SQLAlchemy
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from urza.config.settings import settings

# Create sync engine
engine = create_engine(
    settings.database_url_sync,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False  # Set to True for SQL query logging during development
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """
    Dependency for getting DB session in FastAPI endpoints.
    
    Usage:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            users = db.query(models.User).all()
            return users
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()