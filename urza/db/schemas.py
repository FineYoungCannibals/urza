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

class ProofofWork(BaseModel):
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

class BaseTask(BaseModel):
    task_id: str
    config: dict
    capability_id: str # FK Capability
    platform_id: str # FK platform
    assigned_to: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    timeout_seconds: int = 3600
    status: TaskStatus = TaskStatus.BROADCASTED
    proof_of_work: Optional[str] = None # FK proof of work
    proof_of_work_required: Optional[bool] = False

class Bot(BaseModel):
    bot_id: str
    username: str
    platform_id: str
    capabilities: list[str]
    s3_access_key: Optional[str] = None
    s3_auth_key: Optional[str] = None
    tg_bot_token: Optional[str]
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_checkin: Optional[datetime]=None