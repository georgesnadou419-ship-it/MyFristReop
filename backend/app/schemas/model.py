from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ModelBase(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    display_name: str | None = None
    model_type: str | None = None
    framework: str | None = None
    model_path: str | None = None
    container_image: str | None = None
    launch_command: str | None = None
    config_json: dict[str, Any] | None = None
    replicas: int = 1
    gpu_requirement: str | None = None
    api_format: str = "openai"
    description: str | None = None


class ModelCreate(ModelBase):
    pass


class ModelUpdate(BaseModel):
    display_name: str | None = None
    model_type: str | None = None
    framework: str | None = None
    model_path: str | None = None
    container_image: str | None = None
    launch_command: str | None = None
    config_json: dict[str, Any] | None = None
    status: str | None = None
    replicas: int | None = None
    gpu_requirement: str | None = None
    api_format: str | None = None
    description: str | None = None


class ModelInstanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    model_id: str
    node_id: str
    container_id: str | None
    assigned_gpu_indices: list[int] | None
    port: int | None
    status: str
    api_endpoint: str | None
    started_at: datetime


class ModelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    display_name: str | None
    model_type: str | None
    framework: str | None
    model_path: str | None
    container_image: str | None
    launch_command: str | None
    config_json: dict[str, Any] | None
    status: str
    replicas: int
    gpu_requirement: str | None
    api_format: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class ModelDeployResponse(BaseModel):
    model: ModelRead
    instances: list[ModelInstanceRead]
