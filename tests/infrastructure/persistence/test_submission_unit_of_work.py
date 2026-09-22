import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.domain.assessment import Assignment, GradingPolicy, IOTestCase
from app.domain.identity import Email, User, UserRole
from app.domain.submission import SourceCode, Submission
from app.infrastructure.persistence import (
    Base,
    SqlAlchemySubmissionUnitOfWork,
)
from app.infrastructure.persistence.models import SubmissionModel
from app.infrastructure.persistence.repositories import (
    SqlAlchemyAssignmentRepository,
    SqlAlchemyUserRepository,
)


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


def prepare_entities(session: Session) -> tuple[int, int]:
    users = SqlAlchemyUserRepository(session)

    instructor = users.save(
        User.register(
            email=Email("teacher@example.com"),
            password_hash="hashed",
            role=UserRole.INSTRUCTOR,
        )
    )
    student = users.save(
        User.register(
            email=Email("student@example.com"),
            password_hash="hashed",
            role=UserRole.STUDENT,
        )
    )
    session.commit()

    assert instructor.id is not None
    assert student.id is not None

    assignment = Assignment.create(
        instructor_id=instructor.id,
        title="Python Basics",
        description="Complete the exercise.",
        grading_policy=GradingPolicy(
            io_weight=100,
            unit_weight=0,
            static_weight=0,
        ),
    )
    assignment.add_io_test_case(
        instructor_id=instructor.id,
        test_case=IOTestCase(
            name="basic",
            expected_stdout="ok",
            points=100,
        ),
    )
    assignment.publish(instructor_id=instructor.id)
    SqlAlchemyAssignmentRepository(session).save(assignment)
    session.commit()

    assert assignment.id is not None
    return assignment.id, student.id


def test_submission_unit_of_work_exposes_required_repositories(
    session: Session,
) -> None:
    unit_of_work = SqlAlchemySubmissionUnitOfWork(session)

    assert unit_of_work.assignments is not None
    assert unit_of_work.submissions is not None


def test_submission_unit_of_work_commit_persists_submission(
    session: Session,
) -> None:
    assignment_id, student_id = prepare_entities(session)
    unit_of_work = SqlAlchemySubmissionUnitOfWork(session)

    submission = unit_of_work.submissions.save(
        Submission.queue(
            assignment_id=assignment_id,
            student_id=student_id,
            attempt_number=1,
            source_code=SourceCode("print('hello')"),
        )
    )
    unit_of_work.commit()

    assert session.get(SubmissionModel, submission.id) is not None


def test_submission_unit_of_work_rollback_discards_submission(
    session: Session,
) -> None:
    assignment_id, student_id = prepare_entities(session)
    unit_of_work = SqlAlchemySubmissionUnitOfWork(session)

    submission = unit_of_work.submissions.save(
        Submission.queue(
            assignment_id=assignment_id,
            student_id=student_id,
            attempt_number=1,
            source_code=SourceCode("print('hello')"),
        )
    )
    submission_id = submission.id
    unit_of_work.rollback()

    assert session.get(SubmissionModel, submission_id) is None
