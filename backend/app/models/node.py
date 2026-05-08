from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Node(Base):
    __tablename__ = "nodes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    hostname: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ip: Mapped[str] = mapped_column(String(45), unique=True, nullable=False)
    agent_port: Mapped[int] = mapped_column(Integer, default=9000)
    gpu_count: Mapped[int] = mapped_column(Integer, default=0)
    gpu_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    total_memory_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="offline")
    cpu_percent: Mapped[float] = mapped_column(Float, default=0.0)
    memory_percent: Mapped[float] = mapped_column(Float, default=0.0)
    last_heartbeat: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    gpus: Mapped[list["GpuDevice"]] = relationship(
        back_populates="node",
        cascade="all, delete-orphan",
        order_by="GpuDevice.gpu_index",
    )
    tasks: Mapped[list["Task"]] = relationship(back_populates="assigned_node")
    gpu_metrics: Mapped[list["GpuMetric"]] = relationship(back_populates="node")
    running_containers: Mapped[list["RunningContainer"]] = relationship(
        back_populates="node",
        cascade="all, delete-orphan",
    )
    instances: Mapped[list["ModelInstance"]] = relationship(back_populates="node")


class GpuDevice(Base):
    __tablename__ = "gpu_devices"
    __table_args__ = (UniqueConstraint("node_id", "gpu_index", name="uq_gpu_device_node_index"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    node_id: Mapped[str] = mapped_column(ForeignKey("nodes.id"), nullable=False, index=True)
    gpu_index: Mapped[int] = mapped_column(Integer, nullable=False)
    gpu_uuid: Mapped[str | None] = mapped_column(String(128), nullable=True)
    gpu_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    memory_total_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    memory_used_mb: Mapped[int] = mapped_column(Integer, default=0)
    memory_free_mb: Mapped[int] = mapped_column(Integer, default=0)
    utilization: Mapped[int] = mapped_column(Integer, default=0)
    utilization_memory: Mapped[int] = mapped_column(Integer, default=0)
    temperature: Mapped[int] = mapped_column(Integer, default=0)
    power_usage: Mapped[int] = mapped_column(Integer, default=0)
    power_limit: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="idle")
    processes: Mapped[list[dict]] = mapped_column(JSON, default=list)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    node: Mapped["Node"] = relationship(back_populates="gpus")

    @property
    def utilization_gpu(self) -> int:
        return self.utilization

    @utilization_gpu.setter
    def utilization_gpu(self, value: int) -> None:
        self.utilization = value


class RunningContainer(Base):
    __tablename__ = "running_containers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    node_id: Mapped[str] = mapped_column(ForeignKey("nodes.id"), nullable=False, index=True)
    container_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    task_id: Mapped[str | None] = mapped_column(ForeignKey("tasks.id"), nullable=True, index=True)
    image: Mapped[str | None] = mapped_column(String(256), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="running")
    gpu_indices: Mapped[list[int]] = mapped_column(JSON, default=list)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    node: Mapped["Node"] = relationship(back_populates="running_containers")
