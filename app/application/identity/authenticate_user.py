from __future__ import annotations

from dataclasses import dataclass

from app.domain.identity import Email

from .dto import IdentityUser
from .errors import InactiveUserError, InvalidCredentialsError
from .ports import IdentityUnitOfWork, PasswordHasher


@dataclass(frozen=True, slots=True)
class AuthenticateUserCommand:
    email: str
    password: str


class AuthenticateUser:
    """Authenticate credentials without issuing transport-specific tokens."""

    def __init__(
        self,
        *,
        unit_of_work: IdentityUnitOfWork,
        password_hasher: PasswordHasher,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._password_hasher = password_hasher

    def execute(self, command: AuthenticateUserCommand) -> IdentityUser:
        email = Email(command.email)
        user = self._unit_of_work.users.get_by_email(email)

        if user is None:
            raise InvalidCredentialsError("Invalid email or password.")

        if not self._password_hasher.verify(
            command.password,
            user.password_hash,
        ):
            raise InvalidCredentialsError("Invalid email or password.")

        if not user.is_active:
            raise InactiveUserError("Account is deactivated.")

        return IdentityUser.from_domain(user)
