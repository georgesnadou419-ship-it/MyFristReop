import os
from dataclasses import dataclass


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://suit:suit123@postgres:5432/suitdb",
    )
    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    agent_port: int = _get_int("AGENT_PORT", 9000)
    schedule_interval: int = _get_int("SCHEDULE_INTERVAL", 1)
    task_volume_root: str = os.getenv("TASK_VOLUME_ROOT", "/data/tasks")
    workspace_mount_path: str = os.getenv("WORKSPACE_MOUNT_PATH", "/workspace")
    agent_timeout: int = _get_int("AGENT_TIMEOUT", 30)
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
