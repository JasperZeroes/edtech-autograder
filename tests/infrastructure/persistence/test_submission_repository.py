import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.domain.assessment import (
    Assignment,
    GradingPolicy,
    IOTestCase,
)
from app.domain.identity import Email, User, UserRole
from app.domain.submission import SourceCode, Submission, SubmissionStatus
from app.infrastructure.persistence import Base
from app.infrastructure.persistence.models import SubmissionModel
from app.infrastructure.persistence.repositories import (
    SqlAlchemyAssignmentRepository,
    SqlAlchemySubmissionRepository,
    SqlAlchemyUserRepository,
    SubmissionPersistenceError,
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


def persist_user(
    session: Session,
    *,
    email: str,
    role: UserRole,
) -> int:
    user = SqlAlchemyUserRepository(session).save(
        User.register(
            email=Email(email),
            password_hash="hashed-password",
            role=role,
        )
    )
    session.commit()
    assert user.id is not None
    return user.id


def persist_published_assignment(
    session: Session,
    *,
    instructor_id: int,
) -> int:
    assignment = Assignment.create(
        instructor_id=instructor_id,
        title="Python Basics",
        description="Complete the exercise.",
        grading_policy=GradingPolicy(
            io_weight=100,
            unit_weight=0,
            static_weight=0,
        ),
    )
    assignment.add_io_test_case(
        instructor_id=instructor_id,
        test_case=IOTestCase(
            name="basic",
            expected_stdout="ok",
            points=100,
        ),
    )
    assignment.publish(instructor_id=instructor_id)
    SqlAlchemyAssignmentRepository(session).save(assignment)
    session.commit()
    assert assignment.id is not None
    return assignment.id


def make_submission(
    *,
    assignment_id: int,
    student_id: int,
    attempt_number: int = 1,
) -> Submission:
    return Submission.queue(
        assignment_id=assignment_id,
        student_id=student_id,
        attempt_number=attempt_number,
        source_code=SourceCode("print('hello')"),
    )


def test_save_and_get_submission_rehydrates_domain_state(
    session: Session,
) -> None:
    instructor_id = persist_user(
        session,
        email="teacher@example.com",
        role=UserRole.INSTRUCTOR,
    )
    student_id = persist_user(
        session,
        email="student@example.com",
        role=UserRole.STUDENT,
    )
    assignment_id = persist_published_assignment(
        session,
        instructor_id=instructor_id,
    )
    repository = SqlAlchemySubmissionRepository(session)

    submission = repository.save(
        make_submission(
            assignment_id=assignment_id,
            student_id=student_id,
        )
    )
    session.commit()
    session.expire_all()

    loaded = repository.get_by_id(submission.id)  # type: ignore[arg-type]

    assert loaded is not None
    assert loaded.assignment_id == assignment_id
    assert loaded.student_id == student_id
    assert loaded.attempt_number == 1
    assert loaded.status is SubmissionStatus.QUEUED
    assert loaded.source_code.content == "print('hello')"


def test_next_attempt_number_increments_per_student_assignment(
    session: Session,
) -> None:
    instructor_id = persist_user(
        session,
        email="teacher@example.com",
        role=UserRole.INSTRUCTOR,
    )
    first_student = persist_user(
        session,
        email="student1@example.com",
        role=UserRole.STUDENT,
    )
    second_student = persist_user(
        session,
        email="student2@example.com",
        role=UserRole.STUDENT,
    )
    assignment_id = persist_published_assignment(
        session,
        instructor_id=instructor_id,
    )
    repository = SqlAlchemySubmissionRepository(session)

    assert repository.next_attempt_number(
        assignment_id=assignment_id,
        student_id=first_student,
    ) == 1

    repository.save(
        make_submission(
            assignment_id=assignment_id,
            student_id=first_student,
            attempt_number=1,
        )
    )
    session.commit()

    assert repository.next_attempt_number(
        assignment_id=assignment_id,
        student_id=first_student,
    ) == 2
    assert repository.next_attempt_number(
        assignment_id=assignment_id,
        student_id=second_student,
    ) == 1


def test_multiple_attempts_are_preserved(
    session: Session,
) -> None:
    instructor_id = persist_user(
        session,
        email="teacher@example.com",
        role=UserRole.INSTRUCTOR,
    )
    student_id = persist_user(
        session,
        email="student@example.com",
        role=UserRole.STUDENT,
    )
    assignment_id = persist_published_assignment(
        session,
        instructor_id=instructor_id,
    )
    repository = SqlAlchemySubmissionRepository(session)

    first = make_submission(
        assignment_id=assignment_id,
        student_id=student_id,
        attempt_number=1,
    )
    second = Submission.queue(
        assignment_id=assignment_id,
        student_id=student_id,
        attempt_number=2,
        source_code=SourceCode("print('second')"),
    )
    repository.save(first)
    repository.save(second)
    session.commit()

    results = repository.list_by_student(student_id)

    assert [item.attempt_number for item in results] == [1, 2]
    assert [item.source_code.content for item in results] == [
        "print('hello')",
        "print('second')",
    ]


def test_repository_persists_lifecycle_changes(
    session: Session,
) -> None:
    instructor_id = persist_user(
        session,
        email="teacher@example.com",
        role=UserRole.INSTRUCTOR,
    )
    student_id = persist_user(
        session,
        email="student@example.com",
        role=UserRole.STUDENT,
    )
    assignment_id = persist_published_assignment(
        session,
        instructor_id=instructor_id,
    )
    repository = SqlAlchemySubmissionRepository(session)

    submission = repository.save(
        make_submission(
            assignment_id=assignment_id,
            student_id=student_id,
        )
    )
    session.commit()

    submission.start_grading()
    repository.save(submission)
    session.commit()

    submission.fail_grading(reason="execution timed out")
    repository.save(submission)
    session.commit()
    session.expire_all()

    loaded = repository.get_by_id(submission.id)  # type: ignore[arg-type]

    assert loaded is not None
    assert loaded.status is SubmissionStatus.FAILED
    assert loaded.failure_reason == "execution timed out"


def test_list_by_assignment_filters_other_assignments(
    session: Session,
) -> None:
    instructor_id = persist_user(
        session,
        email="teacher@example.com",
        role=UserRole.INSTRUCTOR,
    )
    student_id = persist_user(
        session,
        email="student@example.com",
        role=UserRole.STUDENT,
    )
    first_assignment = persist_published_assignment(
        session,
        instructor_id=instructor_id,
    )

    second = Assignment.create(
        instructor_id=instructor_id,
        title="Second Assignment",
        description="Another exercise.",
        grading_policy=GradingPolicy(
            io_weight=100,
            unit_weight=0,
            static_weight=0,
        ),
    )
    second.add_io_test_case(
        instructor_id=instructor_id,
        test_case=IOTestCase(
            name="basic",
            expected_stdout="ok",
            points=100,
        ),
    )
    second.publish(instructor_id=instructor_id)
    SqlAlchemyAssignmentRepository(session).save(second)
    session.commit()
    assert second.id is not None

    repository = SqlAlchemySubmissionRepository(session)
    repository.save(
        make_submission(
            assignment_id=first_assignment,
            student_id=student_id,
        )
    )
    repository.save(
        make_submission(
            assignment_id=second.id,
            student_id=student_id,
        )
    )
    session.commit()

    results = repository.list_by_assignment(first_assignment)

    assert len(results) == 1
    assert results[0].assignment_id == first_assignment


def test_duplicate_attempt_number_is_rejected_by_database(
    session: Session,
) -> None:
    instructor_id = persist_user(
        session,
        email="teacher@example.com",
        role=UserRole.INSTRUCTOR,
    )
    student_id = persist_user(
        session,
        email="student@example.com",
        role=UserRole.STUDENT,
    )
    assignment_id = persist_published_assignment(
        session,
        instructor_id=instructor_id,
    )

    session.add_all(
        [
            SubmissionModel(
                assignment_id=assignment_id,
                student_id=student_id,
                attempt_number=1,
                source_code="print('first')",
                status="queued",
            ),
            SubmissionModel(
                assignment_id=assignment_id,
                student_id=student_id,
                attempt_number=1,
                source_code="print('duplicate')",
                status="queued",
            ),
        ]
    )

    with pytest.raises(IntegrityError):
        session.flush()

    session.rollback()


def test_missing_persisted_submission_cannot_be_updated(
    session: Session,
) -> None:
    repository = SqlAlchemySubmissionRepository(session)
    submission = Submission(
        id=999,
        assignment_id=1,
        student_id=1,
        attempt_number=1,
        source_code=SourceCode("print('hello')"),
    )

    with pytest.raises(SubmissionPersistenceError):
        repository.save(submission)
