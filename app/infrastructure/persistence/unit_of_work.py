from __future__ import annotations

from sqlalchemy.orm import Session

from app.infrastructure.persistence.repositories import SqlAlchemyUserRepository


class SqlAlchemyIdentityUnitOfWork:
    """SQLAlchemy transaction boundary for identity use cases."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self.users = SqlAlchemyUserRepository(session)

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
