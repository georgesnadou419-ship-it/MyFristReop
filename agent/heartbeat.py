import logging
import os
import socket
import threading
from datetime import datetime, timezone
from typing import Callable

import requests

from container_tracker import ContainerTracker
from gpu_monitor import collect_gpu_info
from resource_monitor import collect_resource_info

LOGGER = logging.getLogger("suit-agent.heartbeat")


def _default_ip() -> str:
    hostname = socket.gethostname()
    try:
        return socket.gethostbyname(hostname)
    except OSError:
        return "127.0.0.1"


class HeartbeatReporter:
    def __init__(self, container_tracker: ContainerTracker, node_id_getter: Callable[[], str]):
        self.container_tracker = container_tracker
        self.node_id_getter = node_id_getter
        self.control_plane = os.getenv("CONTROL_PLANE", "").rstrip("/")
        self.node_name = os.getenv("NODE_NAME", socket.gethostname())
        self.node_ip = os.getenv("NODE_IP", _default_ip())
        self.agent_port = int(os.getenv("AGENT_PORT", "9000"))
        self.interval = int(os.getenv("HEARTBEAT_INTERVAL", "10"))
        self.timeout = int(os.getenv("HEARTBEAT_TIMEOUT", "5"))
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self):
        if not self.control_plane:
            raise ValueError("CONTROL_PLANE environment variable is required")
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True, name="heartbeat-reporter")
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)

    def _run(self):
        while not self._stop_event.is_set():
            try:
                payload = self.build_payload()
                response = requests.post(
                    f"{self.control_plane}/api/v1/nodes/heartbeat",
                    json=payload,
                    timeout=self.timeout,
                )
                response.raise_for_status()
            except Exception as exc:
                LOGGER.warning("heartbeat failed: %s", exc)
            self._stop_event.wait(self.interval)

    def build_payload(self) -> dict:
        payload = {
            "node_id": self.node_id_getter(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "hostname": self.node_name,
            "ip": self.node_ip,
            "agent_port": self.agent_port,
            "gpus": collect_gpu_info(),
            "cpu": {},
            "memory": {},
            "disk": {},
            "running_containers": self.container_tracker.list_managed_containers(),
        }
        resources = collect_resource_info()
        payload["cpu"] = {
            "percent": resources.get("cpu_percent", 0),
            "cores": resources.get("cpu_cores", 0),
            "load_average": resources.get("load_average", []),
        }
        payload["memory"] = {
            "total": resources.get("memory_total", 0),
            "used": resources.get("memory_used", 0),
            "available": resources.get("memory_available", 0),
            "percent": resources.get("memory_percent", 0),
        }
        payload["disk"] = {
            "total": resources.get("disk_total", 0),
            "used": resources.get("disk_used", 0),
            "free": resources.get("disk_free", 0),
            "percent": resources.get("disk_percent", 0),
        }
        return payload
