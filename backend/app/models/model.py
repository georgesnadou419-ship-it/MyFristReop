import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Model(Base):
    __tablename__ = "models"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    model_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    framework: Mapped[str | None] = mapped_column(String(32), nullable=True)
    model_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    container_image: Mapped[str | None] = mapped_column(String(256), nullable=True)
    launch_command: Mapped[str | None] = mapped_column(Text, nullable=True)
    config_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="offline", nullable=False)
    replicas: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    gpu_requirement: Mapped[str | None] = mapped_column(String(64), nullable=True)
    api_format: Mapped[str] = mapped_column(String(32), default="openai", nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    instances: Mapped[list["ModelInstance"]] = relationship(back_populates="model", cascade="all, delete-orphan")


class ModelInstance(Base):
    __tablename__ = "model_instances"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    model_id: Mapped[str] = mapped_column(ForeignKey("models.id"), nullable=False, index=True)
    node_id: Mapped[str] = mapped_column(ForeignKey("nodes.id"), nullable=False, index=True)
    container_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    assigned_gpu_indices: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)
    port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="starting", nullable=False)
    api_endpoint: Mapped[str | None] = mapped_column(String(256), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    model: Mapped[Model] = relationship(back_populates="instances")
    node: Mapped["Node"] = relationship(back_populates="instances")
