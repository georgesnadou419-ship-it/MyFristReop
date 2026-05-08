from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.model import ModelCreate, ModelDeployResponse, ModelInstanceRead, ModelRead, ModelUpdate
from app.services.model_service import ModelService
from app.utils.responses import success_response

router = APIRouter(prefix="/api/v1/models", tags=["models"])


@router.post("")
def create_model(
    payload: ModelCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    model = ModelService(db).create_model(payload)
    return success_response(ModelRead.model_validate(model).model_dump(mode="json"))


@router.get("")
def list_models(db: Session = Depends(get_db)):
    models = ModelService(db).list_models()
    return success_response([ModelRead.model_validate(model).model_dump(mode="json") for model in models])


@router.get("/{model_id}")
def get_model(model_id: str, db: Session = Depends(get_db)):
    model = ModelService(db).get_model(model_id)
    return success_response(ModelRead.model_validate(model).model_dump(mode="json"))


@router.put("/{model_id}")
def update_model(
    model_id: str,
    payload: ModelUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    model = ModelService(db).update_model(model_id, payload)
    return success_response(ModelRead.model_validate(model).model_dump(mode="json"))


@router.delete("/{model_id}")
def delete_model(
    model_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ModelService(db).delete_model(model_id)
    return success_response(None)


@router.post("/{model_id}/deploy")
def deploy_model(
    model_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    model, instances = ModelService(db).deploy_model(model_id)
    payload = ModelDeployResponse.model_validate(
        {
            "model": ModelRead.model_validate(model).model_dump(mode="json"),
            "instances": [ModelInstanceRead.model_validate(instance).model_dump(mode="json") for instance in instances],
        }
    )
    return success_response(payload.model_dump(mode="json"))


@router.post("/{model_id}/stop")
def stop_model(
    model_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    model = ModelService(db).stop_model(model_id)
    return success_response(ModelRead.model_validate(model).model_dump(mode="json"))


@router.get("/{model_id}/instances")
def list_model_instances(model_id: str, db: Session = Depends(get_db)):
    instances = ModelService(db).list_instances(model_id)
    return success_response([ModelInstanceRead.model_validate(instance).model_dump(mode="json") for instance in instances])
