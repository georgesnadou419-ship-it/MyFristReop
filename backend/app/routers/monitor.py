from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.monitor import GpuMetricPoint, NodeOverview
from app.services.monitor_service import get_gpu_history, get_nodes_overview
from app.utils.responses import success_response


router = APIRouter(prefix="/api/v1/monitor", tags=["monitor"])


@router.get("/gpu/history")
def gpu_history(
    node_id: str = Query(..., description="Node ID"),
    gpu_index: int | None = Query(default=None),
    hours: int = Query(default=24, ge=1, le=168),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    data = [
        GpuMetricPoint.model_validate(item).model_dump(mode="json")
        for item in get_gpu_history(db, node_id=node_id, gpu_index=gpu_index, hours=hours)
    ]
    return success_response(data)


@router.get("/nodes/overview")
def nodes_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    data = [NodeOverview.model_validate(item).model_dump(mode="json") for item in get_nodes_overview(db)]
    return success_response(data)
