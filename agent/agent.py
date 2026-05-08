import logging
import os
from contextlib import asynccontextmanager
from typing import Annotated

from docker.errors import DockerException, NotFound
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from container_tracker import ContainerTracker
from heartbeat import HeartbeatReporter

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))


class RunRequest(BaseModel):
    task_id: str
    image: str
    gpus: list[int] = Field(default_factory=list)
    command: str
    volumes: dict[str, str] = Field(default_factory=dict)
    env: dict[str, str] = Field(default_factory=dict)
    ports: dict[str, int] = Field(default_factory=dict)


class StopRequest(BaseModel):
    container_id: str


NODE_ID = os.getenv("NODE_NAME", "node-unknown")
tracker: ContainerTracker | None = None
heartbeat: HeartbeatReporter | None = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    global tracker, heartbeat
    tracker = ContainerTracker()
    heartbeat = HeartbeatReporter(tracker, lambda: NODE_ID)
    heartbeat.start()
    try:
        yield
    finally:
        if heartbeat is not None:
            heartbeat.stop()
        if tracker is not None:
            tracker.close()


app = FastAPI(title="SUIT Node Agent", lifespan=lifespan)


def require_tracker() -> ContainerTracker:
    if tracker is None:
        raise HTTPException(status_code=503, detail="docker tracker is not initialized")
    return tracker

@app.get("/api/health")
def health():
    return {"status": "ok", "node_id": NODE_ID}


@app.post("/api/run")
def run_container(payload: RunRequest):
    try:
        container = require_tracker().run_container(
            task_id=payload.task_id,
            image=payload.image,
            gpus=payload.gpus,
            command=payload.command,
            volumes=payload.volumes,
            env=payload.env,
            ports=payload.ports,
        )
    except DockerException as exc:
        raise HTTPException(status_code=500, detail=f"failed to start container: {exc}") from exc

    return {"container_id": container.id, "status": container.status}


@app.post("/api/stop")
def stop_container(payload: StopRequest):
    try:
        require_tracker().stop_container(payload.container_id)
    except NotFound as exc:
        raise HTTPException(status_code=404, detail="container not found") from exc
    except DockerException as exc:
        raise HTTPException(status_code=500, detail=f"failed to stop container: {exc}") from exc

    return {"status": "stopped"}


@app.get("/api/logs/{container_id}")
def get_logs(container_id: str, tail: Annotated[int, Query(ge=1, le=5000)] = 100):
    try:
        logs = require_tracker().get_logs(container_id, tail=tail)
    except NotFound as exc:
        raise HTTPException(status_code=404, detail="container not found") from exc
    except DockerException as exc:
        raise HTTPException(status_code=500, detail=f"failed to fetch logs: {exc}") from exc

    return {"logs": logs}
