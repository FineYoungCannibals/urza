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
    BROADCASTED = "broadcasted"
    CLAIMED = "claimed"
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

class Platform(Base):
    __tablename__ = "platforms"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    os_major_version = Column(String(50))
    
    # Relationships
    bots = relationship("Bot", back_populates="platform")
    tasks = relationship("Task", back_populates="platform")

class Capability(Base):
    __tablename__ = "capabilities"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    version = Column(String(50), nullable=False)
    description = Column(Text)
    
    # Note: bot_capabilities junction table needed for many-to-many

class BotCapability(Base):
    __tablename__ = "bot_capabilities"
    
    bot_id = Column(String(36), ForeignKey("bots.bot_id"), primary_key=True)
    capability_id = Column(String(36), ForeignKey("capabilities.id"), primary_key=True)

class Bot(Base):
    __tablename__ = "bots"
    
    bot_id = Column(String(36), primary_key=True)
    created_by_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    platform_id = Column(String(36), ForeignKey("platforms.id"), nullable=False)
    tg_bot_username = Column(String(255), nullable=False)
    tg_bot_token = Column(String(255), nullable=False)
    last_checkin = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    is_hidden = Column(Boolean, default=False)
    
    # Relationships
    created_by = relationship("User", back_populates="bots")
    platform = relationship("Platform", back_populates="bots")
    task_executions = relationship("TaskExecution", back_populates="bot")

class NotificationConfig(Base):
    __tablename__ = "notification_configs"
    
    id = Column(String(36), primary_key=True)
    profile_name = Column(String(255), nullable=False)
    profile_description = Column(Text)
    created_by_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    webhook_url = Column(String(512), nullable=True)
    telegram_chat_id = Column(String(255), nullable=True)
    slack_webhook_url = Column(String(512), nullable=True)
    slack_channel = Column(String(255), nullable=True)
    notify_on_task_completed = Column(Boolean, default=True)
    notify_on_task_error = Column(Boolean, default=True)
    notify_on_task_timeout = Column(Boolean, default=True)
    notify_on_bot_offline = Column(Boolean, default=False)
    
    # Relationships
    tasks = relationship("Task", back_populates="notification_config")

class Task(Base):
    __tablename__ = "tasks"
    
    task_id = Column(String(36), primary_key=True)
    config = Column(JSON, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    capability_id = Column(String(36), ForeignKey("capabilities.id"), nullable=False)
    platform_id = Column(String(36), ForeignKey("platforms.id"), nullable=False)
    created_by_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    notification_config_id = Column(String(36), ForeignKey("notification_configs.id"), nullable=True)
    next_run = Column(DateTime, nullable=True)
    last_run = Column(DateTime, nullable=True)
    timeout_seconds = Column(Integer, default=3600)
    cron_schedule = Column(String(255), nullable=True)
    proof_of_work_required = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    is_hidden = Column(Boolean, default=False)
    
    # Relationships
    created_by = relationship("User", back_populates="tasks")
    platform = relationship("Platform", back_populates="tasks")
    notification_config = relationship("NotificationConfig", back_populates="tasks")
    executions = relationship("TaskExecution", back_populates="task")

class ProofOfWork(Base):
    __tablename__ = "proof_of_work"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    link = Column(String(512), nullable=False)
    description = Column(Text, nullable=True)
    
    # Relationships
    task_executions = relationship("TaskExecution", back_populates="proof_of_work")

class TaskExecution(Base):
    __tablename__ = "task_executions"
    
    execution_id = Column(String(36), primary_key=True)
    task_id = Column(String(36), ForeignKey("tasks.task_id"), nullable=False)
    created_by_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    assigned_to = Column(String(36), ForeignKey("bots.bot_id"), nullable=True)
    started_at = Column(DateTime, default=lambda: datetime.now(UTC))
    completed_at = Column(DateTime, nullable=True)
    status = Column(SQLEnum(TaskStatusEnum), default=TaskStatusEnum.BROADCASTED)
    proof_of_work_id = Column(String(36), ForeignKey("proof_of_work.id"), nullable=True)
    error_message = Column(Text, nullable=True)
    results = Column(JSON, nullable=True)
    retry_count = Column(Integer, default=0)
    is_hidden = Column(Boolean, default=False)
    
    # Relationships
    task = relationship("Task", back_populates="executions")
    bot = relationship("Bot", back_populates="task_executions")
    proof_of_work = relationship("ProofOfWork", back_populates="task_executions")

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