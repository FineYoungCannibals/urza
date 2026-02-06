# urza/db/models.py
# This is a models.py file created to define the data types used by alembic to handle schema changes.
from sqlalchemy import (
    Column, String, Boolean, Integer, DateTime, Text, 
    ForeignKey, JSON, Enum as SQLEnum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime, UTC
import enum

Base = declarative_base()

class TaskStatusEnum(str, enum.Enum):
    PENDING = "pending"
    BROADCASTED = "broadcasted"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEDOUT = "timedout"

class UserRole(Base):
    __tablename__ = "user_roles"
    
    name = Column(String(255), primary_key=True)
    description = Column(Text)
    admin = Column(Boolean, default=False)
    can_see_hidden = Column(Boolean, default=False)
    # Relationships
    users = relationship("User", back_populates="role")

class User(Base):
    __tablename__ = "users"
    
    user_id = Column(String(36), primary_key=True)
    username = Column(String(255), unique=True, nullable=False)
    role_name = Column(String(255), ForeignKey("user_roles.name"), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    created_by_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    is_active = Column(Boolean, default=True)
    is_hidden = Column(Boolean, default=False)
    
    # Relationships
    role = relationship("UserRole", back_populates="users")
    created_by = relationship("User", remote_side=[user_id], foreign_keys=[created_by_id])
    api_keys = relationship("APIKey", back_populates="user", foreign_keys="APIKey.user_id")
    bots = relationship("Bot", back_populates="created_by")
    tasks = relationship("Task", back_populates="created_by")

class Bot(Base):
    __tablename__ = "bots"
    
    bot_id = Column(String(36), primary_key=True)
    tg_bot_username = Column(String(255), nullable=False)
    tg_bot_token = Column(String(255), nullable=False)
    last_checkin = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    created_by_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    is_hidden = Column(Boolean, default=False)
    
    # Relationships
    created_by = relationship("User", back_populates="bots")
    task_executions = relationship("TaskExecution", back_populates="bot")

class Task(Base):
    __tablename__ = "tasks"
    
    task_id = Column(String(36), primary_key=True)
    config = Column(JSON, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_by_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    next_run = Column(DateTime, nullable=True)
    last_run = Column(DateTime, nullable=True)
    timeout_seconds = Column(Integer, default=3600)
    cron_schedule = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    is_hidden = Column(Boolean, default=False)
    
    # Relationships
    created_by = relationship("User", back_populates="tasks")
    executions = relationship("TaskExecution", back_populates="task")

class TaskExecution(Base):
    __tablename__ = "task_executions"
    
    execution_id = Column(String(36), primary_key=True)
    task_id = Column(String(36), ForeignKey("tasks.task_id"), nullable=False)
    assigned_to = Column(String(36), ForeignKey("bots.bot_id"), nullable=True)
    submitted_at = Column(DateTime, default=lambda: datetime.now(UTC))
    queued_at = Column(DateTime, nullable=True)
    claimed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    status = Column(SQLEnum(TaskStatusEnum), default=TaskStatusEnum.BROADCASTED)
    error_message = Column(Text, nullable=True)
    results = Column(JSON, nullable=True)
    retry_count = Column(Integer, default=0)
    is_hidden = Column(Boolean, default=False)
    
    # Relationships
    task = relationship("Task", back_populates="executions")
    bot = relationship("Bot", back_populates="task_executions")

class APIKey(Base):
    __tablename__ = "api_keys"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    hashed_key = Column(String(255), nullable=False)
    user_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    created_by_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    last_used = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    is_hidden = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User", back_populates="api_keys", foreign_keys=[user_id])