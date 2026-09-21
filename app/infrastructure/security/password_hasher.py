from __future__ import annotations

from argon2 import PasswordHasher as Argon2Hasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError


class Argon2PasswordHasher:
    """Argon2id adapter for the application's password-hashing port."""

    def __init__(self) -> None:
        self._hasher = Argon2Hasher()

    def hash(self, plain_password: str) -> str:
        return self._hasher.hash(plain_password)

    def verify(self, plain_password: str, password_hash: str) -> bool:
        try:
            return self._hasher.verify(password_hash, plain_password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False
