from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.models.api_call import ApiCall
from app.models.billing import BillingRecord
from app.models.task import Task
from app.models.user import User


settings = get_settings()
logger = logging.getLogger(__name__)


def _quantize(value: Decimal, scale: str = "0.0001") -> Decimal:
    return value.quantize(Decimal(scale), rounding=ROUND_HALF_UP)


def _format_duration(duration_seconds: int) -> str:
    hours, remainder = divmod(max(duration_seconds, 0), 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}h{minutes:02d}m"
    if minutes:
        return f"{minutes}m{seconds:02d}s"
    return f"{seconds}s"


def calculate_task_billing(db: Session) -> int:
    tasks = db.execute(
        select(Task)
        .where(Task.status == "success", Task.billed.is_(False))
        .where(Task.started_at.is_not(None), Task.finished_at.is_not(None))
        .options(selectinload(Task.user), selectinload(Task.assigned_node))
    ).scalars().all()

    billed_count = 0
    for task in tasks:
        if task.started_at is None or task.finished_at is None:
            continue

        duration = max(int((task.finished_at - task.started_at).total_seconds()), 0)
        gpu_count = len(task.assigned_gpu_indices or [])
        if duration == 0 or gpu_count == 0:
            task.billed = True
            billed_count += 1
            continue

        cost = Decimal(str(duration)) / Decimal("3600")
        cost *= Decimal(str(gpu_count)) * Decimal(str(settings.gpu_hour_rate))
        cost = _quantize(cost)

        record = BillingRecord(
            user_id=task.user_id,
            task_id=task.id,
            resource_type="gpu_time",
            gpu_model=task.assigned_node.gpu_model if task.assigned_node else None,
            duration_seconds=duration,
            cost_credits=cost,
            created_at=task.finished_at or datetime.now(timezone.utc),
        )

        user = task.user
        if user is not None:
            current = Decimal(user.credits)
            if current < cost:
                logger.warning("skip gpu_time billing for task %s because user %s has insufficient credits", task.id, user.id)
                continue
            user.credits = _quantize(current - cost, "0.01")

        db.add(record)

        task.billed = True
        billed_count += 1

    db.commit()
    return billed_count


def record_api_call(
    db: Session,
    *,
    user_id: str | None,
    api_key: str | None,
    model_name: str | None,
    endpoint: str,
    tokens_input: int,
    tokens_output: int,
    latency_ms: int | None,
    status_code: int | None,
) -> ApiCall:
    api_call = ApiCall(
        user_id=user_id,
        api_key=api_key,
        model_name=model_name,
        endpoint=endpoint,
        tokens_input=tokens_input,
        tokens_output=tokens_output,
        latency_ms=latency_ms,
        status_code=status_code,
    )
    db.add(api_call)

    total_cost = (
        Decimal(str(tokens_input)) / Decimal("1000") * Decimal(str(settings.api_input_rate_per_1k_tokens))
        + Decimal(str(tokens_output)) / Decimal("1000") * Decimal(str(settings.api_output_rate_per_1k_tokens))
    )
    total_cost = _quantize(total_cost)

    if user_id and total_cost > 0:
        user = db.get(User, user_id)
        if user is not None:
            current = Decimal(user.credits)
            if current < total_cost:
                logger.warning("skip api_call billing for user %s because credits are insufficient", user_id)
            else:
                record = BillingRecord(
                    user_id=user_id,
                    task_id=None,
                    resource_type="api_call",
                    gpu_model=model_name,
                    duration_seconds=0,
                    cost_credits=total_cost,
                )
                db.add(record)
                user.credits = _quantize(current - total_cost, "0.01")

    db.commit()
    db.refresh(api_call)
    return api_call


def get_billing_summary(db: Session, user: User) -> dict:
    used = db.execute(
        select(func.coalesce(func.sum(BillingRecord.cost_credits), 0)).where(BillingRecord.user_id == user.id)
    ).scalar_one()
    used_credits = _quantize(Decimal(used or 0))
    remaining = _quantize(Decimal(user.credits), "0.01")
    total_credits = _quantize(remaining + used_credits, "0.01")
    return {
        "total_credits": total_credits,
        "used_credits": used_credits,
        "remaining": remaining,
    }


def list_billing_records(db: Session, user: User, page: int = 1, page_size: int = 20) -> dict:
    page = max(page, 1)
    page_size = max(min(page_size, 100), 1)

    total = db.execute(select(func.count(BillingRecord.id)).where(BillingRecord.user_id == user.id)).scalar_one()
    stmt = (
        select(BillingRecord, Task.name)
        .outerjoin(Task, Task.id == BillingRecord.task_id)
        .where(BillingRecord.user_id == user.id)
        .order_by(BillingRecord.created_at.desc(), BillingRecord.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = db.execute(stmt).all()

    items = [
        {
            "id": record.id,
            "task_id": record.task_id,
            "task_name": task_name,
            "resource_type": record.resource_type,
            "gpu_model": record.gpu_model,
            "duration_seconds": record.duration_seconds,
            "duration_display": _format_duration(record.duration_seconds),
            "cost": record.cost_credits,
            "created_at": record.created_at,
        }
        for record, task_name in rows
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size}
