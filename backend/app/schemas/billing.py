from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class BillingSummary(BaseModel):
    total_credits: Decimal
    used_credits: Decimal
    remaining: Decimal


class BillingRecordItem(BaseModel):
    id: int
    task_id: str | None = None
    task_name: str | None = None
    resource_type: str
    gpu_model: str | None = None
    duration_seconds: int
    duration_display: str
    cost: Decimal
    created_at: datetime


class BillingRecordsPage(BaseModel):
    items: list[BillingRecordItem]
    total: int
    page: int
    page_size: int
