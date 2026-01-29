"""
Pydantic schemas for API request/response validation
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ==================== BOT SCHEMAS ====================

class BotCreateRequest(BaseModel):
    """Request to create a new bot"""
    platform: str = Field(..., description="Target platform: windows, macos, linux")
    name: Optional[str] = Field(None, description="Bot display name")
    capabilities: Optional[List[str]] = Field(None, description="Bot capabilities")


class BotResponse(BaseModel):
    """Bot information response"""
    bot_id: str
    username: str
    token: str
    platform: str
    spaces_key_id: Optional[str] = None
    status: str
    created_at: datetime
    last_checkin: Optional[datetime] = None


class BotListResponse(BaseModel):
    """List of bots response"""
    bots: List[BotResponse]
    total: int


class BotDeleteRequest(BaseModel):
    """Request to delete a bot"""
    revoke_token: bool = Field(True, description="Also revoke token in Telegram")


# ==================== TASK SCHEMAS ====================

class TaskCreateRequest(BaseModel):
    """Request to create a new task"""
    task_type: str = Field(..., description="Task type: single_bot, all_bots, update_framework")
    target: Optional[str] = Field(None, description="Target for task (IP, domain, etc)")
    assigned_bot_id: Optional[str] = Field(None, description="Specific bot to assign (for single_bot)")
    data: Optional[dict] = Field(None, description="Additional task data")


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


# ==================== FRAMEWORK UPDATE SCHEMAS ====================

class ModuleUpdateRequest(BaseModel):
    """Request to update a framework on bots"""
    framework_name: str = Field(..., description="Framework name (e.g., 'rbp')")
    version: str = Field(..., description="Version to update to")
    target_bots: Optional[List[str]] = Field(None, description="Specific bots to update (None = all)")


# ==================== HEALTH/STATUS SCHEMAS ====================

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