from __future__ import annotations

from typing import Protocol

from app.domain.identity import UserRepository


class PasswordHasher(Protocol):
    """Application port for password hashing and verification."""

    def hash(self, plain_password: str) -> str:
        ...

    def verify(self, plain_password: str, password_hash: str) -> bool:
        ...


class IdentityUnitOfWork(Protocol):
    """Transaction boundary for identity application use cases."""

    users: UserRepository

    def commit(self) -> None:
        ...

    def rollback(self) -> None:
        ...
