from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Numeric
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import UniqueConstraint
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column


class Base(DeclarativeBase):
    pass


class Node(Base):
    __tablename__ = "nodes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    hostname: Mapped[str | None] = mapped_column(String(128))
    ip: Mapped[str] = mapped_column(String(45), unique=True, nullable=False)
    agent_port: Mapped[int] = mapped_column(Integer, default=9000, nullable=False)
    gpu_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    gpu_model: Mapped[str | None] = mapped_column(String(64))
    total_memory_mb: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="offline", nullable=False)
    last_heartbeat: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class GpuDevice(Base):
    __tablename__ = "gpu_devices"
    __table_args__ = (UniqueConstraint("node_id", "gpu_index"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    node_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("nodes.id"),
        nullable=False,
        index=True,
    )
    gpu_index: Mapped[int] = mapped_column(Integer, nullable=False)
    gpu_model: Mapped[str | None] = mapped_column(String(64))
    memory_total_mb: Mapped[int | None] = mapped_column(Integer)
    memory_used_mb: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    utilization: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    temperature: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    power_usage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="idle", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))
    name: Mapped[str | None] = mapped_column(String(128))
    task_type: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    assigned_node_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("nodes.id"),
    )
    assigned_gpu_indices: Mapped[list[int] | None] = mapped_column(ARRAY(Integer))
    container_image: Mapped[str | None] = mapped_column(String(256))
    container_command: Mapped[str | None] = mapped_column(Text)
    container_id: Mapped[str | None] = mapped_column(String(64))
    config_json: Mapped[dict | None] = mapped_column(JSONB)
    result_json: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TaskLog(Base):
    __tablename__ = "task_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tasks.id"),
        nullable=False,
        index=True,
    )
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="user", nullable=False)
    gpu_quota: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    api_key: Mapped[str | None] = mapped_column(String(128), unique=True)
    credits: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
