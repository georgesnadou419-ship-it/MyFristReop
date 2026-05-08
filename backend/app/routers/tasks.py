from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.task import TaskCallbackRequest, TaskCreate
from app.services.task_service import TaskService
from app.utils.responses import success_response

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = TaskService(db).create_task(current_user, payload)
    return success_response({"id": task.id, "status": task.status})


@router.get("")
def list_tasks(
    status_value: str | None = Query(default=None, alias="status"),
    task_type: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = TaskService(db).list_tasks(
        current_user=current_user,
        status_value=status_value,
        task_type=task_type,
        page=page,
        page_size=page_size,
    )
    return success_response(data)


@router.get("/{task_id}")
def get_task_detail(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = TaskService(db).get_task_detail(task_id=task_id, current_user=current_user)
    return success_response(data)


@router.post("/{task_id}/submit")
def submit_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = TaskService(db).submit_task(task_id=task_id, current_user=current_user)
    return success_response({"status": task.status})


@router.post("/{task_id}/cancel")
def cancel_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = TaskService(db).cancel_task(task_id=task_id, current_user=current_user)
    return success_response({"status": task.status})


@router.post("/{task_id}/callback")
def task_callback(
    task_id: str,
    payload: TaskCallbackRequest,
    db: Session = Depends(get_db),
):
    task = TaskService(db).handle_callback(task_id=task_id, payload=payload)
    return success_response({"id": task.id, "status": task.status})


@router.get("/{task_id}/logs")
def get_task_logs(
    task_id: str,
    tail: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logs = TaskService(db).get_task_logs(task_id=task_id, current_user=current_user, tail=tail)
    return success_response({"logs": logs})


@router.delete("/{task_id}")
def delete_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    TaskService(db).delete_task(task_id=task_id, current_user=current_user)
    return success_response({"id": task_id, "deleted": True})

