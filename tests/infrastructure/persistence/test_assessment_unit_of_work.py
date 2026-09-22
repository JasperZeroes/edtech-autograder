import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.domain.assessment import Assignment
from app.domain.identity import Email, User, UserRole
from app.infrastructure.persistence import (
    Base,
    SqlAlchemyAssessmentUnitOfWork,
)
from app.infrastructure.persistence.models import AssignmentModel
from app.infrastructure.persistence.repositories import SqlAlchemyUserRepository


@pytest.fixture
def session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine, expire_on_commit=False) as db_session:
        yield db_session

    Base.metadata.drop_all(engine)
    engine.dispose()


def persist_instructor(session: Session) -> int:
    user = SqlAlchemyUserRepository(session).save(
        User.register(
            email=Email("teacher@example.com"),
            password_hash="hashed-password",
            role=UserRole.INSTRUCTOR,
        )
    )
    session.commit()
    assert user.id is not None
    return user.id


def test_assessment_unit_of_work_exposes_assignment_repository(
    session: Session,
) -> None:
    instructor_id = persist_instructor(session)
    unit_of_work = SqlAlchemyAssessmentUnitOfWork(session)

    assignment = unit_of_work.assignments.save(
        Assignment.create(
            instructor_id=instructor_id,
            title="Python Basics",
            description="Complete the exercise.",
        )
    )

    assert assignment.id is not None


def test_assessment_unit_of_work_commit_persists_assignment(
    session: Session,
) -> None:
    instructor_id = persist_instructor(session)
    unit_of_work = SqlAlchemyAssessmentUnitOfWork(session)

    assignment = unit_of_work.assignments.save(
        Assignment.create(
            instructor_id=instructor_id,
            title="Python Basics",
            description="Complete the exercise.",
        )
    )
    unit_of_work.commit()

    assert session.get(AssignmentModel, assignment.id) is not None


def test_assessment_unit_of_work_rollback_discards_assignment(
    session: Session,
) -> None:
    instructor_id = persist_instructor(session)
    unit_of_work = SqlAlchemyAssessmentUnitOfWork(session)

    assignment = unit_of_work.assignments.save(
        Assignment.create(
            instructor_id=instructor_id,
            title="Python Basics",
            description="Complete the exercise.",
        )
    )
    assignment_id = assignment.id
    unit_of_work.rollback()

    assert session.get(AssignmentModel, assignment_id) is None
