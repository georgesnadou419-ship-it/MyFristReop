from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import GpuDevice
from models import Node
from models import Task


@dataclass(slots=True)
class Allocation:
    node_id: str
    node_ip: str
    agent_port: int
    gpu_indices: list[int]


class GpuAllocator:
    def allocate(self, session: Session, task: Task, nodes: list[Node]) -> Allocation | None:
        config = task.config_json or {}
        required_gpu_count = int(config.get("gpu_count", 1) or 0)
        required_model = config.get("gpu_model")
        min_memory_mb = config.get("min_memory_mb")

        if required_gpu_count <= 0:
            target_node = self._select_node_for_cpu_task(session, nodes)
            if target_node is None:
                return None
            return Allocation(
                node_id=target_node.id,
                node_ip=target_node.ip,
                agent_port=target_node.agent_port,
                gpu_indices=[],
            )

        candidates: list[tuple[Node, list[GpuDevice]]] = []

        for node in nodes:
            stmt = (
                select(GpuDevice)
                .where(
                    GpuDevice.node_id == node.id,
                    GpuDevice.status == "idle",
                )
                .order_by(GpuDevice.gpu_index.asc())
                .with_for_update()
            )
            available_gpus = list(session.scalars(stmt))
            filtered_gpus = [
                gpu
                for gpu in available_gpus
                if self._matches_requirements(gpu, required_model, min_memory_mb)
            ]
            if len(filtered_gpus) >= required_gpu_count:
                candidates.append((node, filtered_gpus))

        if not candidates:
            return None

        candidates.sort(
            key=lambda item: (
                -len(item[1]),
                sum(gpu.utilization for gpu in item[1][:required_gpu_count]) / required_gpu_count,
                item[0].id,
            )
        )
        selected_node, selected_gpus = candidates[0]
        assigned = selected_gpus[:required_gpu_count]

        for gpu in assigned:
            gpu.status = "allocated"

        session.flush()

        return Allocation(
            node_id=selected_node.id,
            node_ip=selected_node.ip,
            agent_port=selected_node.agent_port,
            gpu_indices=[gpu.gpu_index for gpu in assigned],
        )

    def release(self, session: Session, allocation: Allocation) -> None:
        if not allocation.gpu_indices:
            return

        stmt = (
            select(GpuDevice)
            .where(
                GpuDevice.node_id == allocation.node_id,
                GpuDevice.gpu_index.in_(allocation.gpu_indices),
            )
            .with_for_update()
        )
        for gpu in session.scalars(stmt):
            gpu.status = "idle"
        session.flush()

    def release_by_task(self, session: Session, task_id: str) -> None:
        task = session.get(Task, task_id)
        if task is None or not task.assigned_node_id or not task.assigned_gpu_indices:
            return

        allocation = Allocation(
            node_id=task.assigned_node_id,
            node_ip="",
            agent_port=0,
            gpu_indices=list(task.assigned_gpu_indices),
        )
        self.release(session, allocation)

    def _select_node_for_cpu_task(self, session: Session, nodes: list[Node]) -> Node | None:
        if not nodes:
            return None

        def score(node: Node) -> tuple[int, str]:
            stmt = select(GpuDevice).where(
                GpuDevice.node_id == node.id,
                GpuDevice.status == "idle",
            )
            idle_gpu_count = len(list(session.scalars(stmt)))
            return (-idle_gpu_count, node.id)

        return sorted(nodes, key=score)[0]

    @staticmethod
    def _matches_requirements(
        gpu: GpuDevice,
        required_model: str | None,
        min_memory_mb: int | None,
    ) -> bool:
        if required_model and (gpu.gpu_model or "").find(required_model) < 0:
            return False
        if min_memory_mb and (gpu.memory_total_mb or 0) < int(min_memory_mb):
            return False
        return True
