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


class ProofofWork(BaseModel):
    name: str
    description: Optional[str] = None
    link: str


class TaskType(str, Enum):
    RBP="rbp"

class BaseTask(BaseModel):
    task_id: str
    task_type: TaskType
    assigned_to: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    timeout_seconds: int = 3600
    status: TaskStatus = TaskStatus.BROADCASTED
    proof_of_work: Optional[ProofofWork] = None
    proof_of_work_required: Optional[bool] = False

class RBPTask(BaseTask):
    task_type: Literal[TaskType.RBP] = TaskType.RBP
    yaml_config: str

class Platform(str,Enum):
    mac = "mac"
    win = "win"
    ubu = "ubu"

class Bot(BaseModel):
    name: str
    platform: Platform
    capabilities: list[TaskType]