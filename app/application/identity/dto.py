from __future__ import annotations

from dataclasses import dataclass

from app.domain.identity import User, UserRole


@dataclass(frozen=True, slots=True)
class IdentityUser:
    """Safe application result that never exposes a password hash."""

    id: int
    email: str
    role: UserRole
    full_name: str | None
    is_active: bool

    @classmethod
    def from_domain(cls, user: User) -> "IdentityUser":
        if user.id is None:
            raise ValueError("A persisted user id is required.")

        return cls(
            id=user.id,
            email=user.email.value,
            role=user.role,
            full_name=user.full_name,
            is_active=user.is_active,
        )
