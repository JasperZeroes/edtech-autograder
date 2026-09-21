from __future__ import annotations

from dataclasses import dataclass

from app.domain.identity import Email, User, UserRole

from .dto import IdentityUser
from .errors import DuplicateEmailError, InvalidPasswordError
from .ports import IdentityUnitOfWork, PasswordHasher

_MIN_PASSWORD_LENGTH = 8
_MAX_PASSWORD_LENGTH = 128


@dataclass(frozen=True, slots=True)
class RegisterUserCommand:
    email: str
    password: str
    role: UserRole
    full_name: str | None = None


class RegisterUser:
    """Register a new active student or instructor."""

    def __init__(
        self,
        *,
        unit_of_work: IdentityUnitOfWork,
        password_hasher: PasswordHasher,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._password_hasher = password_hasher

    def execute(self, command: RegisterUserCommand) -> IdentityUser:
        email = Email(command.email)
        self._validate_password(command.password)

        if self._unit_of_work.users.get_by_email(email) is not None:
            raise DuplicateEmailError(
                "A user with this email address already exists."
            )

        password_hash = self._password_hasher.hash(command.password)
        user = User.register(
            email=email,
            password_hash=password_hash,
            role=command.role,
            full_name=command.full_name,
        )

        try:
            saved_user = self._unit_of_work.users.save(user)
            self._unit_of_work.commit()
        except Exception:
            self._unit_of_work.rollback()
            raise

        return IdentityUser.from_domain(saved_user)

    @staticmethod
    def _validate_password(password: str) -> None:
        if not _MIN_PASSWORD_LENGTH <= len(password) <= _MAX_PASSWORD_LENGTH:
            raise InvalidPasswordError(
                "Password must be between 8 and 128 characters."
            )
