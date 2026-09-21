from __future__ import annotations

from app.domain.identity import Email, User


class FakeUserRepository:
    def __init__(self, users: list[User] | None = None) -> None:
        self._users_by_id: dict[int, User] = {}
        self._users_by_email: dict[str, User] = {}
        self._next_id = 1

        for user in users or []:
            self.save(user)

    def get_by_id(self, user_id: int) -> User | None:
        return self._users_by_id.get(user_id)

    def get_by_email(self, email: Email) -> User | None:
        return self._users_by_email.get(email.value)

    def save(self, user: User) -> User:
        if user.id is None:
            user.id = self._next_id
            self._next_id += 1
        else:
            self._next_id = max(self._next_id, user.id + 1)

        self._users_by_id[user.id] = user
        self._users_by_email[user.email.value] = user
        return user


class FakeIdentityUnitOfWork:
    def __init__(self, users: list[User] | None = None) -> None:
        self.users = FakeUserRepository(users)
        self.committed = False
        self.rolled_back = False

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True


class FakePasswordHasher:
    def __init__(self) -> None:
        self.hashed_passwords: list[str] = []
        self.verified_passwords: list[tuple[str, str]] = []

    def hash(self, plain_password: str) -> str:
        self.hashed_passwords.append(plain_password)
        return f"hashed::{plain_password}"

    def verify(self, plain_password: str, password_hash: str) -> bool:
        self.verified_passwords.append((plain_password, password_hash))
        return password_hash == f"hashed::{plain_password}"
