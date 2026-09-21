from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.identity import Email, User, UserRepository, UserRole
from app.infrastructure.persistence.models import UserModel


class UserPersistenceError(RuntimeError):
    """Raised when persisted identity state is inconsistent with the domain."""


class SqlAlchemyUserRepository(UserRepository):
    """SQLAlchemy adapter for the identity-domain repository port."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, user_id: int) -> User | None:
        model = self._session.get(UserModel, user_id)
        return self._to_domain(model) if model is not None else None

    def get_by_email(self, email: Email) -> User | None:
        statement = select(UserModel).where(UserModel.email == email.value)
        model = self._session.scalar(statement)
        return self._to_domain(model) if model is not None else None

    def save(self, user: User) -> User:
        if user.id is None:
            model = UserModel(
                email=user.email.value,
                password_hash=user.password_hash,
                role=user.role.value,
                full_name=user.full_name,
                is_active=user.is_active,
            )
            self._session.add(model)
            self._session.flush()
            user.id = model.id
            return user

        model = self._session.get(UserModel, user.id)
        if model is None:
            raise UserPersistenceError(
                f"Cannot update user {user.id}: persistence record does not exist."
            )

        model.email = user.email.value
        model.password_hash = user.password_hash
        model.role = user.role.value
        model.full_name = user.full_name
        model.is_active = user.is_active

        self._session.flush()
        return user

    @staticmethod
    def _to_domain(model: UserModel) -> User:
        return User(
            id=model.id,
            email=Email(model.email),
            password_hash=model.password_hash,
            role=UserRole(model.role),
            full_name=model.full_name,
            is_active=model.is_active,
        )
