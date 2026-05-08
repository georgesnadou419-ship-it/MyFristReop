from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.services.auth_service import AuthService
from app.utils.exceptions import APIError, AppException


def get_current_user(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> User:
    if x_user_id:
        user = db.get(User, x_user_id)
        if user is None:
            raise AppException(status_code=401, message="Invalid X-User-Id header")
        return user

    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        return AuthService(db).get_current_user_by_token(token)

    raise AppException(status_code=401, message="Authentication required")


def get_current_api_user(
    authorization: str = Header(..., alias="Authorization"),
    db: Session = Depends(get_db),
) -> User:
    if not authorization.lower().startswith("bearer "):
        raise APIError(status_code=401, message="Invalid authorization header", code=40101)
    api_key = authorization.split(" ", 1)[1].strip()
    user = AuthService(db).authenticate_api_key(api_key)
    if user is None:
        raise APIError(status_code=401, message="Invalid API key", code=40102)
    return user
