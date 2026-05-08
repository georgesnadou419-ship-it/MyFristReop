from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), default="")
    role: Mapped[str] = mapped_column(String(20), default="user")
    gpu_quota: Mapped[int] = mapped_column(default=2)
    api_key: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    credits: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    tasks: Mapped[list["Task"]] = relationship(back_populates="user")
    billing_records: Mapped[list["BillingRecord"]] = relationship(back_populates="user")
    api_calls: Mapped[list["ApiCall"]] = relationship(back_populates="user")
