from datetime import datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.node import Node
from app.models.task import Task, TaskLog
from app.models.user import User
from app.schemas.task import TaskCallbackRequest, TaskCreate, TaskDetail, TaskLogRead, TaskRead
from app.services.agent_client import AgentClient
from app.services.queue_service import QueueService
from app.utils.exceptions import AppException


class TaskService:
    def __init__(
        self,
        db: Session,
        queue_service: QueueService | None = None,
        agent_client: AgentClient | None = None,
    ):
        self.db = db
        self.queue_service = queue_service or QueueService()
        self.agent_client = agent_client or AgentClient()

    def create_task(self, current_user: User, payload: TaskCreate) -> Task:
        task = Task(
            user_id=current_user.id,
            name=payload.name,
            task_type=payload.task_type,
            status="pending",
            priority=payload.priority,
            container_image=payload.container_image,
            container_command=payload.container_command,
            config_json=payload.config_json.model_dump(),
        )
        self.db.add(task)
        self.db.flush()
        self._add_log(task.id, "system", "task created")
        self.db.commit()
        self.db.refresh(task)
        return task

    def list_tasks(
        self,
        current_user: User,
        status_value: str | None,
        task_type: str | None,
        page: int,
        page_size: int,
    ) -> dict:
        filters = [Task.user_id == current_user.id] if current_user.role != "admin" else []
        if status_value:
            filters.append(Task.status == status_value)
        if task_type:
            filters.append(Task.task_type == task_type)

        count_stmt = select(func.count()).select_from(Task)
        items_stmt = select(Task).order_by(Task.created_at.desc())
        if filters:
            count_stmt = count_stmt.where(*filters)
            items_stmt = items_stmt.where(*filters)

        total = self.db.scalar(count_stmt) or 0
        items = self.db.scalars(
            items_stmt.offset((page - 1) * page_size).limit(page_size)
        ).all()
        return {
            "items": [TaskRead.model_validate(task).model_dump(mode="json") for task in items],
            "total": total,
        }

    def get_task_detail(self, task_id: str, current_user: User) -> dict:
        task = self._get_owned_task(task_id=task_id, current_user=current_user)
        log_stmt = (
            select(TaskLog)
            .where(TaskLog.task_id == task.id)
            .order_by(TaskLog.timestamp.desc())
            .limit(20)
        )
        logs = list(reversed(self.db.scalars(log_stmt).all()))
        detail = TaskDetail(
            **TaskRead.model_validate(task).model_dump(),
            logs=[TaskLogRead.model_validate(log) for log in logs],
        )
        return detail.model_dump(mode="json")

    def submit_task(self, task_id: str, current_user: User) -> Task:
        task = self._get_owned_task(task_id=task_id, current_user=current_user)
        if task.status != "pending":
            raise AppException(status_code=400, message="only pending task can be submitted")

        task.status = "queued"
        self.queue_service.enqueue_task(task.id, task.priority)
        self._add_log(task.id, "system", "task submitted to scheduler queue")
        self.db.commit()
        self.db.refresh(task)
        return task

    def cancel_task(self, task_id: str, current_user: User) -> Task:
        task = self._get_owned_task(task_id=task_id, current_user=current_user)
        if task.status not in {"pending", "queued"}:
            raise AppException(status_code=400, message="only pending or queued task can be cancelled")

        if task.assigned_node_id and task.container_id:
            node = self.db.get(Node, task.assigned_node_id)
            if node:
                self.agent_client.safe_stop_task(
                    node_ip=node.ip,
                    agent_port=node.agent_port,
                    container_id=task.container_id,
                )

        task.status = "cancelled"
        task.finished_at = datetime.now(timezone.utc)
        self._add_log(task.id, "system", "task cancelled")
        self.db.commit()
        self.db.refresh(task)
        return task

    def handle_callback(self, task_id: str, payload: TaskCallbackRequest) -> Task:
        task = self.db.get(Task, task_id)
        if not task:
            raise AppException(status_code=404, message="task not found")

        now = datetime.now(timezone.utc)
        if payload.status == "running":
            task.status = "running"
            task.started_at = task.started_at or now
            if payload.container_id:
                task.container_id = payload.container_id
            self._add_log(task.id, "agent", "task is running")

        if payload.status == "success":
            task.status = "success"
            task.finished_at = now
            if payload.container_id:
                task.container_id = payload.container_id
            task.result_json = {"exit_code": payload.exit_code}
            self._add_log(task.id, "agent", "task finished successfully")

        if payload.status == "failed":
            task.status = "failed"
            task.finished_at = now
            if payload.container_id:
                task.container_id = payload.container_id
            task.result_json = {
                "exit_code": payload.exit_code,
                "error_message": payload.error_message,
            }
            self._add_log(task.id, "agent", "task failed")
            if payload.error_message:
                self._add_log(task.id, "stderr", payload.error_message)

        if payload.logs_chunk:
            self._add_log(task.id, "stdout", payload.logs_chunk)

        self.db.commit()
        self.db.refresh(task)

        if payload.status in {"success", "failed"}:
            self.queue_service.publish_task_finished(task.id)

        return task

    def get_task_logs(self, task_id: str, current_user: User, tail: int) -> list[dict]:
        task = self._get_owned_task(task_id=task_id, current_user=current_user)
        log_stmt = (
            select(TaskLog)
            .where(TaskLog.task_id == task.id)
            .order_by(TaskLog.timestamp.desc())
            .limit(tail)
        )
        logs = list(reversed(self.db.scalars(log_stmt).all()))
        return [TaskLogRead.model_validate(log).model_dump(mode="json") for log in logs]

    def delete_task(self, task_id: str, current_user: User) -> None:
        task = self._get_owned_task(task_id=task_id, current_user=current_user)
        if task.status not in {"success", "failed", "cancelled"}:
            raise AppException(status_code=400, message="only finished task can be deleted")

        self.db.execute(delete(TaskLog).where(TaskLog.task_id == task.id))
        self.db.delete(task)
        self.db.commit()

    def _get_owned_task(self, task_id: str, current_user: User) -> Task:
        task = self.db.get(Task, task_id)
        if not task:
            raise AppException(status_code=404, message="task not found")
        if current_user.role != "admin" and task.user_id != current_user.id:
            raise AppException(status_code=404, message="task not found")
        return task

    def _add_log(self, task_id: str, source: str, message: str) -> None:
        self.db.add(TaskLog(task_id=task_id, source=source, message=message))

