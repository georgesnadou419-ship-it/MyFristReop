from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.node import HeartbeatPayload
from app.services.node_service import NodeService
from app.utils.responses import success_response

router = APIRouter(prefix="/api/v1/nodes", tags=["nodes"])

@router.post("/heartbeat")
def heartbeat(payload: HeartbeatPayload, db: Session = Depends(get_db)):
    node = NodeService.handle_heartbeat(db, payload)
    return success_response({"node_id": node.id})


@router.get("")
def list_nodes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    nodes = NodeService.list_nodes(db)
    return success_response([NodeService.serialize_node(node) for node in nodes])
