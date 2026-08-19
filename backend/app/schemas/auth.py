from pydantic import BaseModel, Field

from app.schemas.user import UserBrief


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=72)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class TokenPairData(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    user: UserBrief


class AccessTokenData(BaseModel):
    access_token: str
    expires_in: int
