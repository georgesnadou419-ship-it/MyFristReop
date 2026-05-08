import secrets

from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.user import User
from app.schemas.user import TokenData, UserCreate, UserLogin
from app.utils.exceptions import AppException
from app.utils.security import create_access_token, get_password_hash, verify_password


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def register_user(self, payload: UserCreate) -> User:
        existing = self.db.scalar(select(User).where(User.username == payload.username))
        if existing:
            raise AppException(status_code=400, message="username already exists")

        user = User(
            username=payload.username,
            password_hash=get_password_hash(payload.password),
            api_key=self._generate_api_key(),
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def login_user(self, payload: UserLogin) -> TokenData:
        user = self.db.scalar(select(User).where(User.username == payload.username))
        if not user or not verify_password(payload.password, user.password_hash):
            raise AppException(status_code=401, message="invalid username or password")
        return TokenData(access_token=create_access_token(user.id), token_type="bearer")

    def authenticate_api_key(self, api_key: str) -> User | None:
        return self.db.scalar(select(User).where(User.api_key == api_key))

    def get_current_user_by_token(self, token: str) -> User:
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret,
                algorithms=[settings.jwt_algorithm],
            )
        except JWTError as exc:
            raise AppException(status_code=401, message="invalid access token") from exc

        user_id = payload.get("sub")
        if not user_id:
            raise AppException(status_code=401, message="invalid access token")

        user = self.db.get(User, user_id)
        if not user:
            raise AppException(status_code=401, message="user not found")
        return user

    @staticmethod
    def _generate_api_key() -> str:
        return f"sk-{secrets.token_urlsafe(24)}"
