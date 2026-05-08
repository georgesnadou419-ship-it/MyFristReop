from datetime import datetime

from pydantic import BaseModel, ConfigDict


class GpuMetricPoint(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    timestamp: datetime
    node_id: str
    gpu_index: int
    utilization: int
    memory_used: int
    memory_total: int
    temperature: int
    power_usage: int


class NodeOverview(BaseModel):
    node_id: str
    hostname: str | None = None
    ip: str
    status: str
    gpu_count: int
    gpu_used: int
    cpu_percent: float
    memory_percent: float
    last_heartbeat: datetime | None = None
