from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime, UTC
from enum import Enum

class TaskStatus(str,Enum):
    BROADCASTED = "broadcasted"
    CLAIMED = "claimed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEDOUT = "timedout"

class ProofOfWork(BaseModel):
    id: str
    name: str
    link: str
    description: Optional[str] = None

class Capability(BaseModel):
    id: str
    name: str
    version: str
    description: str

class Platform(BaseModel):
    id: str
    name: str
    description: str
    os_major_version: str

class NotificationConfig(BaseModel):
    """ Urza will notify channel configurations saved here """
    id: str
    profile_name: str
    profile_description: str
    webhook_url: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    slack_webhook_url: Optional[str] = None
    slack_channel: Optional[str] = None
    notify_on_task_completed: bool = True
    notify_on_task_error: bool = True
    notify_on_task_timeout: bool = True
    notify_on_bot_offline: bool = False

class Task(BaseModel):
    task_id: str
    config: dict
    capability_id: str # FK Capability
    platform_id: str # FK platform
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    notification_config_id: Optional[str] #FK notificationconfig 
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    timeout_seconds: int = 3600
    cron_schedule: Optional[str]  = None
    proof_of_work_required: bool = False
    is_active: bool = True
    is_hidden: bool = False

class TaskResponse(BaseModel):
    task_id: str
    created_at: datetime
    capability_id: str
    config: dict
    cron_schedule: Optional[str] = None
    proof_of_work_required: bool = False

class TaskExecution(BaseModel):
    execution_id: str
    task_id: str # FK task
    assigned_to: Optional[str] = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: Optional[datetime] = None
    status: TaskStatus = TaskStatus.BROADCASTED
    proof_of_work_id: Optional[str] = None# FK proof of work
    error_message: Optional[str] = None
    results: Optional[dict] = None
    retry_count: int = 0
    is_hidden: bool = False

class TaskExecutionResponse(BaseModel):
    execution_id: str
    task_id: str
    status: TaskStatus
    assigned_to: Optional[str] = None
    proof_of_work_id: Optional[str]  = None
    results: Optional[dict] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

# users dont use an endpoint that expects this as a request
# - or expects this as a response, this is for Urza internal
# - use only
class Bot(BaseModel):
    bot_id: str
    username: str
    platform_id: str
    s3_access_key: str
    s3_auth_key: str
    tg_bot_token: str
    capabilities: list[str] 
    last_checkin: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    is_hidden: bool = False

# users will create bots with this Request Object
# only users with  can_create_hidden can use is_hidden
class BotCreateRequest(BaseModel):
    platform_id: str
    capabilities: list[str]
    is_hidden: bool = False

# When a bot is created or lookedup , this class is used
class BotLookupResponse(BaseModel):
    bot_id: str
    username: str
    platform_id: str
    capabilities: list[str]
    created_at: datetime

class BotCreateResponse(BaseModel):
    bot_id: str
    username: str
    platform_id: str
    s3_access_key: str
    s3_auth_key: str
    tg_bot_token: str
    capabilities: list[str] 

class BotCheckin(BaseModel):
    bot_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

class TaskClaimRequest(BaseModel):
    """Bot sends JSON to claim a task via Telegram"""
    execution_id: str # bot generated
    bot_id: str # provided by the bot
    claimed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

class TaskResult(BaseModel):
    """ Bot sends JSON via Telegram with results"""
    execution_id: str
    bot_id: str
    status: TaskStatus
    results: dict 
    error_message: Optional[str] = None
    completed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

class UserRole(BaseModel):
    name: str
    description: str
    admin: bool = False
    can_create_hidden: bool = False
    can_see_hidden: bool = False

class UserRoleResponse(BaseModel):
    name: str
    description: str
    admin: bool

class APIKey(BaseModel):
    id: str
    name: str 
    hashed_key: str # hashed version 
    user_id: str #FK to user
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_used: Optional[datetime] = None
    is_active: bool = True
    is_hidden: bool = False

class APIKeyResponse(BaseModel):
    id: str
    name: str
    user_id: str
    created_at: datetime
    last_used: Optional[datetime] = None
    is_active: bool

class User(BaseModel):
    user_id: str
    username: str
    role: UserRole
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    is_active: bool = True
    is_hidden: bool = False

class UserResponse(BaseModel):
    user_id: str
    username: str
    role_name: str # just return the role name
    description: Optional[str] = None
    created_at: datetime
    is_active: bool