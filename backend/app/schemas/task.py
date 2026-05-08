from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel

TaskType = Literal["train", "inference", "custom"]
TaskStatus = Literal["pending", "queued", "running", "success", "failed", "cancelled"]
CallbackStatus = Literal["running", "success", "failed"]


class TaskConfig(BaseModel):
    gpu_count: int = Field(default=1, ge=1)
    gpu_model: str | None = None
    min_memory_mb: int | None = Field(default=None, ge=0)
    env_vars: dict[str, str] = Field(default_factory=dict)
    max_runtime_seconds: int | None = Field(default=None, ge=1)


class TaskCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    task_type: TaskType
    container_image: str = Field(min_length=1, max_length=256)
    container_command: str = Field(min_length=1)
    priority: int = 0
    config_json: TaskConfig = Field(default_factory=TaskConfig)


class TaskLogRead(ORMModel):
    id: int
    source: str
    message: str
    timestamp: datetime


class TaskRead(ORMModel):
    id: str
    user_id: str
    name: str
    task_type: str
    status: str
    priority: int
    assigned_node_id: str | None
    assigned_gpu_indices: list[int] | None
    container_image: str
    container_command: str
    container_id: str | None
    config_json: dict[str, Any] | None
    result_json: dict[str, Any] | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class TaskDetail(TaskRead):
    logs: list[TaskLogRead] = Field(default_factory=list)


class TaskCallbackRequest(BaseModel):
    status: CallbackStatus
    container_id: str | None = Field(default=None, max_length=64)
    exit_code: int | None = None
    error_message: str | None = None
    logs_chunk: str | None = None

