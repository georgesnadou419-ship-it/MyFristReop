import json
from datetime import datetime, timezone
from typing import Any

import docker
from docker.errors import NotFound
from docker.types import DeviceRequest


class ContainerTracker:
    LABEL_MANAGED = "suit.managed"
    LABEL_TASK_ID = "suit.task_id"
    LABEL_GPU_INDICES = "suit.gpu_indices"

    def __init__(self):
        self.client = docker.from_env()

    def close(self):
        self.client.close()

    def run_container(
        self,
        task_id: str,
        image: str,
        gpus: list[int],
        command: str,
        volumes: dict[str, str],
        env: dict[str, str] | None = None,
        ports: dict[str, int] | None = None,
    ):
        volume_bindings = {
            host_path: {"bind": container_path, "mode": "rw"}
            for host_path, container_path in volumes.items()
        }
        labels = {
            self.LABEL_MANAGED: "true",
            self.LABEL_TASK_ID: task_id,
            self.LABEL_GPU_INDICES: json.dumps(gpus),
        }
        device_requests = None
        if gpus:
            device_requests = [
                DeviceRequest(
                    count=len(gpus),
                    device_ids=[str(index) for index in gpus],
                    capabilities=[["gpu"]],
                )
            ]

        container = self.client.containers.run(
            image=image,
            command=command,
            detach=True,
            volumes=volume_bindings,
            environment=env or None,
            ports=ports or None,
            labels=labels,
            device_requests=device_requests,
        )
        return container

    def stop_container(self, container_id: str):
        container = self.client.containers.get(container_id)
        container.stop(timeout=10)
        container.remove(v=True)

    def get_logs(self, container_id: str, tail: int = 100) -> str:
        container = self.client.containers.get(container_id)
        output = container.logs(stdout=True, stderr=True, tail=tail)
        return output.decode("utf-8", errors="replace")

    def list_managed_containers(self) -> list[dict[str, Any]]:
        containers = self.client.containers.list(
            all=True,
            filters={"label": f"{self.LABEL_MANAGED}=true"},
        )
        result = []
        for container in containers:
            labels = container.labels or {}
            gpu_indices = self._parse_gpu_indices(labels.get(self.LABEL_GPU_INDICES))
            result.append(
                {
                    "container_id": container.id,
                    "task_id": labels.get(self.LABEL_TASK_ID),
                    "image": self._get_image_name(container),
                    "status": container.status,
                    "gpu_indices": gpu_indices,
                    "started_at": self._get_started_at(container),
                }
            )
        return result

    @staticmethod
    def _parse_gpu_indices(value: str | None) -> list[int]:
        if not value:
            return []
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        return [int(index) for index in parsed]

    @staticmethod
    def _get_image_name(container) -> str:
        tags = getattr(container.image, "tags", None) or []
        if tags:
            return tags[0]
        return container.image.short_id

    @staticmethod
    def _get_started_at(container) -> str | None:
        started_at = ((getattr(container, "attrs", None) or {}).get("State") or {}).get("StartedAt")
        if not started_at:
            return None
        try:
            normalized = started_at.replace("Z", "+00:00")
            return datetime.fromisoformat(normalized).astimezone(timezone.utc).isoformat()
        except ValueError:
            return started_at

    def exists(self, container_id: str) -> bool:
        try:
            self.client.containers.get(container_id)
            return True
        except NotFound:
            return False
