from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.schemas.user import CurrentUser, TokenData, UserCreate, UserLogin, UserRegisterResponse
from app.services.auth_service import AuthService
from app.utils.responses import success_response

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register")
def register(payload: UserCreate, db: Session = Depends(get_db)) -> dict:
    user = AuthService(db).register_user(payload)
    return success_response(UserRegisterResponse.model_validate(user).model_dump(mode="json"))


@router.post("/login")
def login(payload: UserLogin, db: Session = Depends(get_db)) -> dict:
    token = AuthService(db).login_user(payload)
    return success_response(TokenData.model_validate(token).model_dump())


@router.get("/me")
def me(user: CurrentUser = Depends(get_current_user)) -> dict:
    return success_response(CurrentUser.model_validate(user).model_dump())
