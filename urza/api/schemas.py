"""
Pydantic schemas for API request/response validation
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from urza.db.schemas import Capability, Platform


# Client requests
class BotCreateRequest(BaseModel):
    """Request to create a new bot"""
    capabilities: list[str]
    platform: str

class BotDeleteRequest(BaseModel):
    """Request to delete a bot"""
    username: Optional[str]
    bot_id: Optional[str]

class TaskCreateRequest(BaseModel):
    """Request to create a new task"""
    config: dict
    required_capability: str
    proof_of_work_required: Optional[bool]
    platform_type: Optional[str]

class CapabilityCreateRequest(BaseModel):
    """
    Docstring for CapabilityCreateRequest
    """
    name: str
    version: str
    description: str

class CapabilityDeleteRequest(BaseModel):
    """
    Docstring for CapabilityDeleteRequest
    """
    name: Optional[str]
    id: Optional[str]
    version: Optional[str]

class CapabilityRequest(BaseModel):
    """
    Docstring for CapabilityRequest
    """
    capabilities: List[Capability]


class  PlatformCreateRequest(BaseModel):
    """
    Docstring for PlatformCreateRequest
    """
    name: str
    description: str
    os_major_version: str


class BotProvisionResponse(BaseModel):
    bot_id: str
    username: str
    s3_access_key: str
    s3_auth_key: str
    tg_bot_token: str


class BotResponse(BaseModel):
    """Bot information response"""
    bot_id: str
    username: str
    urza_auth_token: str
    platform: Platform
    capabilities: list[Capability]
    s3_access_key: str
    s3_auth_key: str
    tg_bot_token: str
    created_at: datetime
    last_checkin: Optional[datetime] = None

class BotListResponse(BaseModel):
    """List of bots response"""
    bots: List[BotResponse]
    total: int

class TaskResponse(BaseModel):
    """Task information response"""
    task_id: str
    task_type: str
    target: Optional[str] = None
    assigned_bot_id: Optional[str] = None
    status: str  # pending, assigned, in_progress, complete, failed
    created_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[dict] = None


class TaskListResponse(BaseModel):
    """List of tasks response"""
    tasks: List[TaskResponse]
    total: int


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: datetime
    telegram_connected: bool
    database_connected: bool


class StatusResponse(BaseModel):
    """System status response"""
    active_bots: int
    pending_tasks: int
    completed_tasks_24h: int
    uptime_seconds: int