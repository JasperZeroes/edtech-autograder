from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class IdentityValidationError(ValueError):
    """Raised when identity data violates a domain invariant."""


class UserRole(str, Enum):
    STUDENT = "student"
    INSTRUCTOR = "instructor"


_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass(frozen=True, slots=True)
class Email:
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()

        if not normalized or not _EMAIL_PATTERN.fullmatch(normalized):
            raise IdentityValidationError("A valid email address is required.")

        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value


@dataclass(slots=True)
class User:
    id: int | None
    email: Email
    password_hash: str
    role: UserRole
    full_name: str | None = None
    is_active: bool = True

    def __post_init__(self) -> None:
        if self.id is not None and self.id <= 0:
            raise IdentityValidationError("User id must be a positive integer.")

        if not self.password_hash or not self.password_hash.strip():
            raise IdentityValidationError("Password hash is required.")

        if not isinstance(self.role, UserRole):
            try:
                self.role = UserRole(self.role)
            except ValueError as exc:
                raise IdentityValidationError(
                    "Role must be either 'student' or 'instructor'."
                ) from exc

        if self.full_name is not None:
            normalized_name = self.full_name.strip()
            self.full_name = normalized_name or None

    @classmethod
    def register(
        cls,
        *,
        email: Email,
        password_hash: str,
        role: UserRole,
        full_name: str | None = None,
    ) -> "User":
        return cls(
            id=None,
            email=email,
            password_hash=password_hash,
            role=role,
            full_name=full_name,
            is_active=True,
        )

    @property
    def is_student(self) -> bool:
        return self.role is UserRole.STUDENT

    @property
    def is_instructor(self) -> bool:
        return self.role is UserRole.INSTRUCTOR

    def deactivate(self) -> None:
        self.is_active = False

    def activate(self) -> None:
        self.is_active = True
