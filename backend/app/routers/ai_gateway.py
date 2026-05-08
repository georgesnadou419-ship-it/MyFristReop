from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_api_user
from app.schemas.ai import ChatCompletionRequest, CompletionRequest, EmbeddingRequest
from app.services.ai_service import AIService

router = APIRouter(tags=["ai-gateway"])


def _extract_bearer_token(authorization: str) -> str:
    return authorization.split(" ", 1)[1].strip()


@router.get("/v1/models")
def list_public_models(db: Session = Depends(get_db)):
    return AIService(db).list_public_models()


@router.post("/v1/chat/completions")
async def chat_completions(
    payload: ChatCompletionRequest,
    authorization: str = Header(..., alias="Authorization"),
    user=Depends(get_current_api_user),
    db: Session = Depends(get_db),
):
    api_key = _extract_bearer_token(authorization)
    return await AIService(db).proxy_chat_completion(payload.model_dump(exclude_none=True), user, api_key)


@router.post("/v1/completions")
async def completions(
    payload: CompletionRequest,
    authorization: str = Header(..., alias="Authorization"),
    user=Depends(get_current_api_user),
    db: Session = Depends(get_db),
):
    api_key = _extract_bearer_token(authorization)
    return await AIService(db).proxy_completion(payload.model_dump(exclude_none=True), user, api_key)


@router.post("/v1/embeddings")
async def embeddings(
    payload: EmbeddingRequest,
    authorization: str = Header(..., alias="Authorization"),
    user=Depends(get_current_api_user),
    db: Session = Depends(get_db),
):
    api_key = _extract_bearer_token(authorization)
    return await AIService(db).proxy_embeddings(payload.model_dump(exclude_none=True), user, api_key)
