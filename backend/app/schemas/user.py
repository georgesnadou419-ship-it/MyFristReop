from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)


class UserLogin(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    role: str
    gpu_quota: int
    created_at: datetime


class CurrentUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    role: str


class UserRegisterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str


class TokenPayload(BaseModel):
    sub: str
    exp: int


class TokenData(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    access_token: str
    token_type: str = "bearer"
