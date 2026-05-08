from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import GpuDevice, Node, RunningContainer
from app.schemas.node import HeartbeatPayload


class NodeService:
    @staticmethod
    def handle_heartbeat(db: Session, payload: HeartbeatPayload) -> Node:
        node = db.scalar(
            select(Node)
            .where(Node.ip == payload.ip)
            .options(selectinload(Node.gpus), selectinload(Node.running_containers))
        )
        if node is None:
            node = Node(ip=payload.ip)
            db.add(node)
            db.flush()

        node.hostname = payload.hostname
        node.ip = payload.ip
        node.agent_port = payload.agent_port
        node.gpu_count = len(payload.gpus)
        node.gpu_model = payload.gpus[0].model if payload.gpus else None
        node.total_memory_mb = payload.memory.total
        node.status = "online"
        node.cpu_percent = payload.cpu.percent
        node.memory_percent = payload.memory.percent
        node.last_heartbeat = payload.timestamp or datetime.now(timezone.utc)

        db.query(RunningContainer).filter(RunningContainer.node_id == node.id).delete()
        active_gpu_indices: set[int] = set()
        for item in payload.running_containers:
            db.add(
                RunningContainer(
                    node_id=node.id,
                    container_id=item.container_id,
                    task_id=item.task_id,
                    image=item.image,
                    status=item.status,
                    gpu_indices=item.gpu_indices,
                    started_at=item.started_at,
                )
            )
            if item.status in {"created", "restarting", "running"}:
                active_gpu_indices.update(item.gpu_indices)

        existing_gpu_map = {gpu.gpu_index: gpu for gpu in node.gpus}
        seen_indices: set[int] = set()
        for gpu_info in payload.gpus:
            seen_indices.add(gpu_info.index)
            gpu = existing_gpu_map.get(gpu_info.index)
            if gpu is None:
                gpu = GpuDevice(node_id=node.id, gpu_index=gpu_info.index)
                db.add(gpu)

            gpu.gpu_uuid = gpu_info.uuid
            gpu.gpu_model = gpu_info.model
            gpu.memory_total_mb = gpu_info.memory_total
            gpu.memory_used_mb = gpu_info.memory_used
            gpu.memory_free_mb = gpu_info.memory_free
            gpu.utilization_gpu = gpu_info.utilization_gpu
            gpu.utilization_memory = gpu_info.utilization_memory
            gpu.temperature = gpu_info.temperature
            gpu.power_usage = gpu_info.power_usage
            gpu.power_limit = gpu_info.power_limit
            gpu.processes = [process.model_dump() for process in gpu_info.processes]
            if gpu_info.index in active_gpu_indices:
                gpu.status = "allocated"
            elif gpu_info.processes or gpu_info.utilization_gpu > 0 or gpu_info.memory_used > 0:
                gpu.status = "busy"
            else:
                gpu.status = "idle"

        stale_gpus = [gpu for index, gpu in existing_gpu_map.items() if index not in seen_indices]
        for gpu in stale_gpus:
            db.delete(gpu)

        db.commit()
        db.refresh(node)
        return node

    @staticmethod
    def list_nodes(db: Session) -> list[Node]:
        return list(
            db.scalars(
                select(Node).options(selectinload(Node.gpus), selectinload(Node.running_containers)).order_by(Node.ip)
            )
        )

    @staticmethod
    def list_idle_gpus(db: Session) -> list[GpuDevice]:
        return list(
            db.scalars(
                select(GpuDevice)
                .join(Node)
                .options(selectinload(GpuDevice.node))
                .where(Node.status == "online", GpuDevice.status == "idle")
                .order_by(Node.ip, GpuDevice.gpu_index)
            )
        )

    @staticmethod
    def serialize_node(node: Node) -> dict:
        return {
            "id": node.id,
            "hostname": node.hostname,
            "ip": node.ip,
            "agent_port": node.agent_port,
            "gpu_count": node.gpu_count,
            "gpu_model": node.gpu_model,
            "total_memory_mb": node.total_memory_mb,
            "status": node.status,
            "cpu_percent": node.cpu_percent,
            "memory_percent": node.memory_percent,
            "last_heartbeat": node.last_heartbeat.isoformat() if node.last_heartbeat else None,
            "gpus": [
                {
                    "id": gpu.id,
                    "gpu_index": gpu.gpu_index,
                    "gpu_uuid": gpu.gpu_uuid,
                    "gpu_model": gpu.gpu_model,
                    "memory_total_mb": gpu.memory_total_mb,
                    "memory_used_mb": gpu.memory_used_mb,
                    "memory_free_mb": gpu.memory_free_mb,
                    "utilization_gpu": gpu.utilization_gpu,
                    "utilization_memory": gpu.utilization_memory,
                    "temperature": gpu.temperature,
                    "power_usage": gpu.power_usage,
                    "power_limit": gpu.power_limit,
                    "status": gpu.status,
                    "processes": gpu.processes,
                    "updated_at": gpu.updated_at.isoformat() if gpu.updated_at else None,
                }
                for gpu in sorted(node.gpus, key=lambda item: item.gpu_index)
            ],
            "running_containers": [
                {
                    "container_id": container.container_id,
                    "task_id": container.task_id,
                    "image": container.image,
                    "status": container.status,
                    "gpu_indices": container.gpu_indices,
                    "updated_at": container.updated_at.isoformat() if container.updated_at else None,
                }
                for container in node.running_containers
            ],
        }

    @staticmethod
    def serialize_gpu(gpu: GpuDevice) -> dict:
        node = gpu.node
        return {
            "node_id": node.id,
            "node_ip": node.ip,
            "hostname": node.hostname,
            "gpu_index": gpu.gpu_index,
            "gpu_uuid": gpu.gpu_uuid,
            "gpu_model": gpu.gpu_model,
            "memory_total_mb": gpu.memory_total_mb,
            "memory_used_mb": gpu.memory_used_mb,
            "memory_free_mb": gpu.memory_free_mb,
            "utilization_gpu": gpu.utilization_gpu,
            "utilization_memory": gpu.utilization_memory,
            "temperature": gpu.temperature,
            "power_usage": gpu.power_usage,
            "power_limit": gpu.power_limit,
            "status": gpu.status,
            "processes": gpu.processes,
            "updated_at": gpu.updated_at.isoformat() if gpu.updated_at else None,
        }
