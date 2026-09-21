from __future__ import annotations

from typing import Protocol

from .user import Email, User


class UserRepository(Protocol):
    """Persistence contract expressed in identity-domain language."""

    def get_by_id(self, user_id: int) -> User | None:
        ...

    def get_by_email(self, email: Email) -> User | None:
        ...

    def save(self, user: User) -> User:
        ...
