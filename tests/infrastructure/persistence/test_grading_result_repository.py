from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.domain.assessment import Assignment, GradingPolicy, IOTestCase
from app.domain.grading import (
    EvaluationOutcome,
    EvaluationStatus,
    GradingComponent,
    GradingResult,
)
from app.domain.identity import Email, User, UserRole
from app.domain.submission import SourceCode, Submission
from app.infrastructure.persistence import Base
from app.infrastructure.persistence.models import (
    EvaluationOutcomeModel,
    GradingResultModel,
)
from app.infrastructure.persistence.repositories import (
    GradingResultPersistenceError,
    SqlAlchemyAssignmentRepository,
    SqlAlchemyGradingResultRepository,
    SqlAlchemySubmissionRepository,
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


def prepare_submission(session: Session) -> int:
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

    submission = SqlAlchemySubmissionRepository(session).save(
        Submission.queue(
            assignment_id=assignment.id,
            student_id=student.id,
            attempt_number=1,
            source_code=SourceCode("print('ok')"),
        )
    )
    session.commit()
    assert submission.id is not None
    return submission.id


def make_result() -> GradingResult:
    return GradingResult.build(
        policy=GradingPolicy(
            io_weight=100,
            unit_weight=0,
            static_weight=0,
        ),
        outcomes=(
            EvaluationOutcome(
                component=GradingComponent.IO,
                name="visible",
                status=EvaluationStatus.PASSED,
                earned_points=40,
                possible_points=40,
                is_hidden=False,
                detail="Output matched expected output.",
            ),
            EvaluationOutcome(
                component=GradingComponent.IO,
                name="hidden",
                status=EvaluationStatus.FAILED,
                earned_points=0,
                possible_points=60,
                is_hidden=True,
                detail="Expected '0'; received '1'.",
            ),
        ),
    )


def test_save_and_rehydrate_grading_result(session: Session) -> None:
    submission_id = prepare_submission(session)
    repository = SqlAlchemyGradingResultRepository(session)

    stored = repository.save(
        submission_id=submission_id,
        result=make_result(),
    )
    session.commit()
    session.expire_all()

    loaded = repository.get_by_submission_id(submission_id)

    assert loaded is not None
    assert loaded.id == stored.id
    assert loaded.submission_id == submission_id
    assert loaded.result.score.final_score == Decimal("40.00")
    assert len(loaded.result.outcomes) == 2
    assert loaded.result.outcomes[0].is_hidden is False
    assert loaded.result.outcomes[1].is_hidden is True
    assert loaded.result.outcomes[1].detail == (
        "Expected '0'; received '1'."
    )


def test_feedback_facts_are_persisted(session: Session) -> None:
    submission_id = prepare_submission(session)
    repository = SqlAlchemyGradingResultRepository(session)

    stored = repository.save(
        submission_id=submission_id,
        result=make_result(),
    )
    session.flush()

    model = session.get(GradingResultModel, stored.id)

    assert model is not None
    assert model.feedback_facts == [
        {
            "kind": "visible_tests",
            "message": "Passed 1 of 1 visible evaluations.",
        },
        {
            "kind": "hidden_tests",
            "message": "Passed 0 of 1 hidden evaluations.",
        },
    ]


def test_evaluation_outcomes_are_persisted_as_child_records(
    session: Session,
) -> None:
    submission_id = prepare_submission(session)
    repository = SqlAlchemyGradingResultRepository(session)

    stored = repository.save(
        submission_id=submission_id,
        result=make_result(),
    )
    session.flush()

    rows = (
        session.query(EvaluationOutcomeModel)
        .filter_by(grading_result_id=stored.id)
        .order_by(EvaluationOutcomeModel.id)
        .all()
    )

    assert len(rows) == 2
    assert rows[0].component == "io"
    assert rows[0].status == "passed"
    assert rows[1].is_hidden is True


def test_repository_refuses_second_result_for_same_submission(
    session: Session,
) -> None:
    submission_id = prepare_submission(session)
    repository = SqlAlchemyGradingResultRepository(session)

    repository.save(
        submission_id=submission_id,
        result=make_result(),
    )
    session.flush()

    with pytest.raises(GradingResultPersistenceError):
        repository.save(
            submission_id=submission_id,
            result=make_result(),
        )


def test_database_enforces_one_result_per_submission(
    session: Session,
) -> None:
    submission_id = prepare_submission(session)

    first = GradingResultModel(
        submission_id=submission_id,
        io_weight=100,
        unit_weight=0,
        static_weight=0,
        io_percentage=Decimal("100.00"),
        unit_percentage=Decimal("0.00"),
        static_percentage=Decimal("0.00"),
        io_contribution=Decimal("100.00"),
        unit_contribution=Decimal("0.00"),
        static_contribution=Decimal("0.00"),
        final_score=Decimal("100.00"),
        feedback_facts=[],
    )
    second = GradingResultModel(
        submission_id=submission_id,
        io_weight=100,
        unit_weight=0,
        static_weight=0,
        io_percentage=Decimal("100.00"),
        unit_percentage=Decimal("0.00"),
        static_percentage=Decimal("0.00"),
        io_contribution=Decimal("100.00"),
        unit_contribution=Decimal("0.00"),
        static_contribution=Decimal("0.00"),
        final_score=Decimal("100.00"),
        feedback_facts=[],
    )
    session.add_all([first, second])

    with pytest.raises(IntegrityError):
        session.flush()

    session.rollback()
