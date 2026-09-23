from __future__ import annotations

from sqlalchemy.orm import Session

from app.infrastructure.persistence.repositories import (
    SqlAlchemyAssignmentRepository,
    SqlAlchemyGradingResultRepository,
    SqlAlchemySubmissionRepository,
    SqlAlchemyUserRepository,
)


class SqlAlchemyIdentityUnitOfWork:
    """SQLAlchemy transaction boundary for identity use cases."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self.users = SqlAlchemyUserRepository(session)

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()


class SqlAlchemyAssessmentUnitOfWork:
    """SQLAlchemy transaction boundary for assessment use cases."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self.assignments = SqlAlchemyAssignmentRepository(session)

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()


class SqlAlchemySubmissionUnitOfWork:
    """SQLAlchemy transaction boundary for submission use cases."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self.assignments = SqlAlchemyAssignmentRepository(session)
        self.submissions = SqlAlchemySubmissionRepository(session)

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()


class SqlAlchemyGradingUnitOfWork:
    """SQLAlchemy transaction boundary for asynchronous grading."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self.assignments = SqlAlchemyAssignmentRepository(session)
        self.submissions = SqlAlchemySubmissionRepository(session)
        self.grading_results = SqlAlchemyGradingResultRepository(session)

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
