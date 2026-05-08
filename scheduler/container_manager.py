from agent_client import AgentClient
from config import settings
from gpu_allocator import Allocation
from models import Task


class ContainerManager:
    def launch(self, task: Task, allocation: Allocation) -> dict:
        if not task.container_image:
            raise ValueError(f"任务 {task.id} 未指定容器镜像")

        volumes = {
            f"{settings.task_volume_root}/{task.id}": settings.workspace_mount_path,
        }

        extra_volumes = (task.config_json or {}).get("volumes", {})
        if isinstance(extra_volumes, dict):
            volumes.update(extra_volumes)

        client = AgentClient(
            node_ip=allocation.node_ip,
            agent_port=allocation.agent_port or settings.agent_port,
            timeout=settings.agent_timeout,
        )
        try:
            return client.launch_task(
                task_id=task.id,
                image=task.container_image,
                gpus=allocation.gpu_indices,
                command=task.container_command or "",
                volumes=volumes,
            )
        finally:
            client.close()

    def stop(self, task: Task, node_ip: str, agent_port: int) -> dict:
        if not task.container_id:
            raise ValueError(f"task {task.id} has no container_id")

        client = AgentClient(
            node_ip=node_ip,
            agent_port=agent_port or settings.agent_port,
            timeout=settings.agent_timeout,
        )
        try:
            return client.stop_task(task.container_id)
        finally:
            client.close()
