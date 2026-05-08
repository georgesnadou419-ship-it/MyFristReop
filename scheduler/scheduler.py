import json
import logging
import threading
import time
from datetime import datetime
from datetime import timezone

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker

from container_manager import ContainerManager
from database import session_scope
from gpu_allocator import GpuAllocator
from models import Node
from models import Task
from models import TaskLog
from queue_manager import QueueManager

logger = logging.getLogger(__name__)


class Scheduler:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        queue_manager: QueueManager,
        allocator: GpuAllocator | None = None,
        container_manager: ContainerManager | None = None,
        schedule_interval: int = 1,
    ):
        self.session_factory = session_factory
        self.queue = queue_manager
        self.allocator = allocator or GpuAllocator()
        self.container_manager = container_manager or ContainerManager()
        self.schedule_interval = schedule_interval
        self._schedule_lock = threading.Lock()

    def run(self) -> None:
        logger.info("scheduler service started")
        self._start_pubsub_listener()

        while True:
            try:
                self._schedule_one()
            except Exception:
                logger.exception("scheduler loop failed")
            time.sleep(self.schedule_interval)

    def _schedule_one(self) -> bool:
        with self._schedule_lock:
            task_data = self.queue.dequeue()
            if not task_data:
                return False

            task_id = task_data.get("task_id")
            if not task_id:
                logger.warning("skip malformed queue payload: %s", task_data)
                return False

            with session_scope(self.session_factory) as session:
                task = session.get(Task, task_id)
                if task is None or task.status != "queued":
                    logger.warning("skip task %s because status is not queued", task_id)
                    return False

                nodes = self._get_online_nodes(session)
                allocation = self.allocator.allocate(session, task, nodes)
                if allocation is None:
                    self.queue.requeue(task_data)
                    self._append_log(
                        session,
                        task_id=task.id,
                        source="system",
                        message="No available GPU or online node, task requeued.",
                    )
                    logger.info("task %s requeued because no resources are available", task.id)
                    return False

                try:
                    result = self.container_manager.launch(task, allocation)
                    container_id = result.get("container_id")
                    if not container_id:
                        raise RuntimeError("agent response missing container_id")

                    task.status = "running"
                    task.assigned_node_id = allocation.node_id
                    task.assigned_gpu_indices = allocation.gpu_indices
                    task.container_id = container_id
                    task.started_at = datetime.now(timezone.utc)
                    task.result_json = result
                    self._append_log(
                        session,
                        task_id=task.id,
                        source="system",
                        message=(
                            f"Task scheduled to node {allocation.node_id}, "
                            f"gpus={allocation.gpu_indices}, container_id={container_id}."
                        ),
                    )
                    logger.info(
                        "task %s started on node %s with gpus %s",
                        task.id,
                        allocation.node_id,
                        allocation.gpu_indices,
                    )
                    return True
                except Exception as exc:
                    self.allocator.release(session, allocation)
                    task.status = "failed"
                    task.result_json = {"error": str(exc)}
                    self._append_log(
                        session,
                        task_id=task.id,
                        source="system",
                        message=f"Task launch failed: {exc}",
                    )
                    logger.exception("task %s launch failed", task.id)
                    return False

    def handle_task_finished(self, task_id: str) -> None:
        if not task_id:
            return

        with self._schedule_lock:
            with session_scope(self.session_factory) as session:
                self.allocator.release_by_task(session, task_id)
                task = session.get(Task, task_id)
                if task is not None:
                    task.assigned_gpu_indices = None
                    self._append_log(
                        session,
                        task_id=task_id,
                        source="system",
                        message="Task finished notification received, GPUs released.",
                    )
                logger.info("released resources for finished task %s", task_id)

        try:
            self._schedule_one()
        except Exception:
            logger.exception("failed to schedule next task after completion of %s", task_id)

    def _get_online_nodes(self, session: Session) -> list[Node]:
        stmt = select(Node).where(Node.status == "online").order_by(Node.id.asc())
        return list(session.scalars(stmt))

    def _append_log(self, session: Session, task_id: str, source: str, message: str) -> None:
        session.add(TaskLog(task_id=task_id, source=source, message=message))
        session.flush()

    def _start_pubsub_listener(self) -> None:
        thread = threading.Thread(target=self._pubsub_listener, daemon=True)
        thread.start()

    def _pubsub_listener(self) -> None:
        while True:
            try:
                pubsub = self.queue.create_pubsub()
                self.queue.subscribe(
                    pubsub,
                    [
                        QueueManager.CHANNEL_NEW_TASK,
                        QueueManager.CHANNEL_TASK_FINISHED,
                    ],
                )
                logger.info("pubsub listener subscribed to redis channels")

                for message in pubsub.listen():
                    data = self._parse_pubsub_message(message.get("data"))
                    channel = message.get("channel")
                    if channel == QueueManager.CHANNEL_TASK_FINISHED:
                        self.handle_task_finished(data.get("task_id", ""))
                    elif channel == QueueManager.CHANNEL_NEW_TASK:
                        self._schedule_one()
            except Exception:
                logger.exception("pubsub listener crashed, retrying in 3 seconds")
                time.sleep(3)

    @staticmethod
    def _parse_pubsub_message(data) -> dict:
        if isinstance(data, dict):
            return data
        if isinstance(data, str):
            try:
                parsed = json.loads(data)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                return {"task_id": data}
        return {}
