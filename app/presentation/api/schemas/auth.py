from __future__ import annotations

from pydantic import BaseModel, Field

from app.application.identity import IdentityUser, TokenPair
from app.domain.identity import UserRole


class UserRegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)
    role: UserRole
    full_name: str | None = None


class UserResponse(BaseModel):
    id: int
    email: str
    role: UserRole
    full_name: str | None
    is_active: bool

    @classmethod
    def from_identity(cls, user: IdentityUser) -> "UserResponse":
        return cls(
            id=user.id,
            email=user.email,
            role=user.role,
            full_name=user.full_name,
            is_active=user.is_active,
        )


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

    @classmethod
    def from_pair(cls, pair: TokenPair) -> "TokenResponse":
        return cls(
            access_token=pair.access_token,
            refresh_token=pair.refresh_token,
        )


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
