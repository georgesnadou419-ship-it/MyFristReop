from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.services.node_service import NodeService
from app.utils.responses import success_response

router = APIRouter(prefix="/api/v1/resources", tags=["resources"])

@router.get("/gpus")
def list_idle_gpus(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    gpus = NodeService.list_idle_gpus(db)
    return success_response([NodeService.serialize_gpu(gpu) for gpu in gpus])
