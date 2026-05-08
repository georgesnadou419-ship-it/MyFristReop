from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, delete, or_, select
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.models.metric import GpuMetric
from app.models.node import Node
from app.models.task import Task


settings = get_settings()


def collect_gpu_metrics(db: Session) -> int:
    nodes = db.execute(
        select(Node).where(Node.status == "online").options(selectinload(Node.gpus))
    ).scalars().all()

    collected = 0
    now = datetime.now(timezone.utc)
    for node in nodes:
        for gpu in node.gpus:
            metric = GpuMetric(
                node_id=node.id,
                gpu_index=gpu.gpu_index,
                utilization=gpu.utilization_gpu or 0,
                memory_used=gpu.memory_used_mb or 0,
                memory_total=gpu.memory_total_mb or 0,
                temperature=gpu.temperature or 0,
                power_usage=gpu.power_usage or 0,
                timestamp=now,
            )
            db.add(metric)
            collected += 1

    cutoff = now - timedelta(days=settings.gpu_metrics_retention_days)
    db.execute(delete(GpuMetric).where(GpuMetric.timestamp < cutoff))
    db.commit()
    return collected


def mark_offline_nodes(db: Session) -> int:
    timeout = datetime.now(timezone.utc) - timedelta(seconds=settings.node_heartbeat_timeout_seconds)
    nodes = db.execute(
        select(Node)
        .where(
            and_(
                Node.status != "offline",
                or_(Node.last_heartbeat.is_(None), Node.last_heartbeat < timeout),
            )
        )
        .options(selectinload(Node.gpus))
    ).scalars().all()

    if not nodes:
        return 0

    node_ids = [node.id for node in nodes]
    impacted_tasks = db.execute(
        select(Task).where(Task.assigned_node_id.in_(node_ids), Task.status.in_(["queued", "running"]))
    ).scalars().all()

    failed_at = datetime.now(timezone.utc)
    for node in nodes:
        node.status = "offline"
        node.cpu_percent = 0
        node.memory_percent = 0
        for gpu in node.gpus:
            gpu.status = "idle"
            gpu.utilization_gpu = 0
            gpu.utilization_memory = 0
            gpu.memory_used_mb = 0
            gpu.memory_free_mb = gpu.memory_total_mb or 0
            gpu.temperature = 0
            gpu.power_usage = 0

    for task in impacted_tasks:
        task.status = "failed"
        task.finished_at = failed_at
        task.result_json = {
            **(task.result_json or {}),
            "reason": "Node heartbeat timeout",
            "failed_at": failed_at.isoformat(),
        }

    db.commit()
    return len(nodes)


def get_gpu_history(db: Session, node_id: str, gpu_index: int | None = None, hours: int = 24) -> list[GpuMetric]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max(hours, 1))
    stmt = select(GpuMetric).where(GpuMetric.node_id == node_id, GpuMetric.timestamp >= cutoff)
    if gpu_index is not None:
        stmt = stmt.where(GpuMetric.gpu_index == gpu_index)
    stmt = stmt.order_by(GpuMetric.timestamp.asc(), GpuMetric.gpu_index.asc())
    return db.execute(stmt).scalars().all()


def get_nodes_overview(db: Session) -> list[dict]:
    nodes = db.execute(select(Node).options(selectinload(Node.gpus)).order_by(Node.ip.asc())).scalars().all()
    overview: list[dict] = []
    for node in nodes:
        gpu_used = sum(
            1
            for gpu in node.gpus
            if gpu.status != "idle" or gpu.utilization_gpu > 0 or gpu.memory_used_mb > 0
        )
        overview.append(
            {
                "node_id": node.id,
                "hostname": node.hostname,
                "ip": node.ip,
                "status": node.status,
                "gpu_count": node.gpu_count or len(node.gpus),
                "gpu_used": gpu_used,
                "cpu_percent": round(node.cpu_percent or 0, 2),
                "memory_percent": round(node.memory_percent or 0, 2),
                "last_heartbeat": node.last_heartbeat,
            }
        )
    return overview
