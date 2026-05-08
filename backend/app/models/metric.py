from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class GpuMetric(Base):
    __tablename__ = "gpu_metrics"
    __table_args__ = (Index("idx_gpu_metrics_node_time", "node_id", "timestamp"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    node_id: Mapped[str] = mapped_column(ForeignKey("nodes.id"), index=True)
    gpu_index: Mapped[int] = mapped_column(Integer, index=True)
    utilization: Mapped[int] = mapped_column(Integer, default=0)
    memory_used: Mapped[int] = mapped_column(Integer, default=0)
    memory_total: Mapped[int] = mapped_column(Integer, default=0)
    temperature: Mapped[int] = mapped_column(Integer, default=0)
    power_usage: Mapped[int] = mapped_column(Integer, default=0)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    node: Mapped["Node"] = relationship(back_populates="gpu_metrics")
