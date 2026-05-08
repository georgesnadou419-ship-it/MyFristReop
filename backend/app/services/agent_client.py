import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class AgentClient:
    def stop_task(self, node_ip: str, agent_port: int, container_id: str) -> dict:
        url = f"http://{node_ip}:{agent_port}/api/stop"
        response = httpx.post(
            url,
            json={"container_id": container_id},
            timeout=settings.agent_timeout,
        )
        response.raise_for_status()
        return response.json()

    def safe_stop_task(self, node_ip: str, agent_port: int, container_id: str) -> None:
        try:
            self.stop_task(node_ip=node_ip, agent_port=agent_port, container_id=container_id)
        except Exception as exc:
            logger.warning("failed to stop container %s on %s:%s: %s", container_id, node_ip, agent_port, exc)
