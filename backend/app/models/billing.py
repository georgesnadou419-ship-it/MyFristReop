from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class BillingRecord(Base):
    __tablename__ = "billing_records"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    task_id: Mapped[str | None] = mapped_column(ForeignKey("tasks.id"), nullable=True, index=True)
    resource_type: Mapped[str] = mapped_column(String(20), default="gpu_time")
    gpu_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    duration_seconds: Mapped[int] = mapped_column(default=0)
    cost_credits: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0.0000"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship(back_populates="billing_records")
    task: Mapped[Optional["Task"]] = relationship(back_populates="billing_records")
