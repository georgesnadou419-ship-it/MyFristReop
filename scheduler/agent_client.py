import httpx


class AgentClient:
    def __init__(self, node_ip: str, agent_port: int = 9000, timeout: int = 30):
        self.base_url = f"http://{node_ip}:{agent_port}"
        self.client = httpx.Client(base_url=self.base_url, timeout=timeout)

    def launch_task(
        self,
        task_id: str,
        image: str,
        gpus: list[int],
        command: str,
        volumes: dict[str, str],
    ) -> dict:
        response = self.client.post(
            "/api/run",
            json={
                "task_id": task_id,
                "image": image,
                "gpus": gpus,
                "command": command,
                "volumes": volumes,
            },
        )
        response.raise_for_status()
        return response.json()

    def stop_task(self, container_id: str) -> dict:
        response = self.client.post(
            "/api/stop",
            json={"container_id": container_id},
        )
        response.raise_for_status()
        return response.json()

    def get_logs(self, container_id: str, tail: int = 100) -> str:
        response = self.client.get(
            f"/api/logs/{container_id}",
            params={"tail": tail},
        )
        response.raise_for_status()
        payload = response.json()
        return payload.get("logs", "")

    def health_check(self) -> bool:
        try:
            response = self.client.get("/api/health")
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    def close(self) -> None:
        self.client.close()
