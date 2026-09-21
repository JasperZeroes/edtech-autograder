from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Protocol

from app.domain.identity import UserRole

from .dto import IdentityUser


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"


@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str
    refresh_token: str


@dataclass(frozen=True, slots=True)
class TokenClaims:
    subject: int
    role: UserRole
    token_type: TokenType
    issued_at: datetime
    expires_at: datetime


class TokenService(Protocol):
    """Application-facing contract for issuing and validating auth tokens."""

    def issue_access(self, user: IdentityUser) -> str:
        ...

    def issue_pair(self, user: IdentityUser) -> TokenPair:
        ...

    def decode(
        self,
        token: str,
        *,
        expected_type: TokenType,
    ) -> TokenClaims:
        ...
