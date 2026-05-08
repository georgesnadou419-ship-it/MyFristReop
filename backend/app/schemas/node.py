from datetime import datetime

from pydantic import BaseModel, Field


class ProcessInfo(BaseModel):
    pid: int
    name: str
    memory_used: int = 0


class GpuInfo(BaseModel):
    index: int
    model: str
    uuid: str | None = None
    memory_total: int = 0
    memory_used: int = 0
    memory_free: int = 0
    utilization_gpu: int = 0
    utilization_memory: int = 0
    temperature: int = 0
    power_usage: int = 0
    power_limit: int = 0
    processes: list[ProcessInfo] = Field(default_factory=list)


class RunningContainerInfo(BaseModel):
    container_id: str
    task_id: str | None = None
    image: str | None = None
    status: str = "running"
    gpu_indices: list[int] = Field(default_factory=list)
    started_at: datetime | None = None


class CpuInfo(BaseModel):
    percent: float = 0
    cores: int = 0
    load_average: list[float] = Field(default_factory=list)


class MemoryInfo(BaseModel):
    total: int = 0
    used: int = 0
    available: int = 0
    percent: float = 0


class DiskInfo(BaseModel):
    total: int = 0
    used: int = 0
    free: int = 0
    percent: float = 0


class HeartbeatPayload(BaseModel):
    node_id: str
    timestamp: datetime | None = None
    hostname: str
    ip: str
    agent_port: int = 9000
    gpus: list[GpuInfo] = Field(default_factory=list)
    cpu: CpuInfo = Field(default_factory=CpuInfo)
    memory: MemoryInfo = Field(default_factory=MemoryInfo)
    disk: DiskInfo = Field(default_factory=DiskInfo)
    running_containers: list[RunningContainerInfo] = Field(default_factory=list)
