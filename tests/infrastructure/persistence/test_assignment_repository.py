import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.domain.assessment import (
    Assignment,
    AssignmentStatus,
    ExecutionLimits,
    GradingPolicy,
    GradingTestVisibility,
    IOTestCase,
    StaticAnalysisRules,
    UnitTestSpecification,
)
from app.domain.identity import Email, User, UserRole
from app.infrastructure.persistence.base import Base
from app.infrastructure.persistence.models import AssignmentModel
from app.infrastructure.persistence.repositories import (
    AssignmentPersistenceError,
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


def persist_instructor(
    session: Session,
    *,
    email: str = "teacher@example.com",
) -> int:
    repository = SqlAlchemyUserRepository(session)
    user = repository.save(
        User.register(
            email=Email(email),
            password_hash="hashed-password",
            role=UserRole.INSTRUCTOR,
            full_name="Teacher One",
        )
    )
    session.commit()

    assert user.id is not None
    return user.id


def make_complete_assignment(instructor_id: int) -> Assignment:
    assignment = Assignment.create(
        instructor_id=instructor_id,
        title="Functions and Control Flow",
        description="Implement the required Python functions.",
        instructions="Submit one Python file.",
        grading_policy=GradingPolicy(
            io_weight=70,
            unit_weight=20,
            static_weight=10,
        ),
        execution_limits=ExecutionLimits(
            max_runtime_ms=5_000,
            max_memory_kb=256_000,
        ),
    )
    assignment.add_io_test_case(
        instructor_id=instructor_id,
        test_case=IOTestCase(
            name="visible example",
            stdin="2 3",
            expected_stdout="5",
            points=40,
            visibility=GradingTestVisibility.VISIBLE,
            order_index=1,
        ),
    )
    assignment.add_io_test_case(
        instructor_id=instructor_id,
        test_case=IOTestCase(
            name="hidden edge case",
            stdin="-1 1",
            expected_stdout="0",
            points=30,
            visibility=GradingTestVisibility.HIDDEN,
            order_index=2,
        ),
    )
    assignment.set_unit_test_spec(
        instructor_id=instructor_id,
        specification=UnitTestSpecification(
            name="function behaviour",
            test_code="assert solve(2, 3) == 5",
            points=20,
            visibility=GradingTestVisibility.HIDDEN,
        ),
    )
    assignment.set_static_analysis_rules(
        instructor_id=instructor_id,
        rules=StaticAnalysisRules(
            required_functions=("solve",),
            forbidden_imports=("os",),
            max_cyclomatic_complexity=10,
            points=10,
        ),
    )
    return assignment


def test_save_new_assignment_assigns_ids_to_aggregate_and_children(
    session: Session,
) -> None:
    instructor_id = persist_instructor(session)
    repository = SqlAlchemyAssignmentRepository(session)
    assignment = make_complete_assignment(instructor_id)

    saved = repository.save(assignment)

    assert saved is assignment
    assert assignment.id is not None
    assert all(test.id is not None for test in assignment.io_test_cases)
    assert assignment.unit_test_spec is not None
    assert assignment.unit_test_spec.id is not None
    assert assignment.static_analysis_rules is not None
    assert assignment.static_analysis_rules.id is not None


def test_get_by_id_rehydrates_complete_domain_aggregate(
    session: Session,
) -> None:
    instructor_id = persist_instructor(session)
    repository = SqlAlchemyAssignmentRepository(session)
    assignment = make_complete_assignment(instructor_id)
    repository.save(assignment)
    session.commit()

    loaded = repository.get_by_id(assignment.id)  # type: ignore[arg-type]

    assert loaded is not None
    assert loaded.id == assignment.id
    assert loaded.instructor_id == instructor_id
    assert loaded.title == "Functions and Control Flow"
    assert loaded.description == "Implement the required Python functions."
    assert loaded.instructions == "Submit one Python file."
    assert loaded.grading_policy == GradingPolicy(70, 20, 10)
    assert loaded.execution_limits == ExecutionLimits(5_000, 256_000)
    assert [test.name for test in loaded.ordered_io_test_cases] == [
        "visible example",
        "hidden edge case",
    ]
    assert loaded.io_test_cases[0].visibility is GradingTestVisibility.VISIBLE
    assert loaded.unit_test_spec is not None
    assert loaded.unit_test_spec.points == 20
    assert loaded.static_analysis_rules is not None
    assert loaded.static_analysis_rules.required_functions == ("solve",)
    assert loaded.static_analysis_rules.forbidden_imports == ("os",)


def test_list_published_excludes_drafts(session: Session) -> None:
    instructor_id = persist_instructor(session)
    repository = SqlAlchemyAssignmentRepository(session)

    draft = make_complete_assignment(instructor_id)
    repository.save(draft)

    published = make_complete_assignment(instructor_id)
    published.title = "Published Assignment"
    published.publish(instructor_id=instructor_id)
    repository.save(published)

    session.commit()

    results = repository.list_published()

    assert [assignment.id for assignment in results] == [published.id]
    assert results[0].status is AssignmentStatus.PUBLISHED


def test_list_by_instructor_filters_other_instructors(
    session: Session,
) -> None:
    first_instructor = persist_instructor(
        session,
        email="teacher1@example.com",
    )
    second_instructor = persist_instructor(
        session,
        email="teacher2@example.com",
    )
    repository = SqlAlchemyAssignmentRepository(session)

    first = make_complete_assignment(first_instructor)
    second = make_complete_assignment(second_instructor)
    repository.save(first)
    repository.save(second)
    session.commit()

    results = repository.list_by_instructor(first_instructor)

    assert len(results) == 1
    assert results[0].id == first.id
    assert results[0].instructor_id == first_instructor


def test_update_persists_aggregate_state(session: Session) -> None:
    instructor_id = persist_instructor(session)
    repository = SqlAlchemyAssignmentRepository(session)
    assignment = make_complete_assignment(instructor_id)
    repository.save(assignment)
    session.commit()

    assignment.publish(instructor_id=instructor_id)
    assignment.configure_execution_limits(
        instructor_id=instructor_id,
        limits=ExecutionLimits(
            max_runtime_ms=10_000,
            max_memory_kb=512_000,
        ),
    )
    repository.save(assignment)
    session.commit()
    session.expire_all()

    loaded = repository.get_by_id(assignment.id)  # type: ignore[arg-type]

    assert loaded is not None
    assert loaded.is_published is True
    assert loaded.execution_limits == ExecutionLimits(10_000, 512_000)


def test_update_can_replace_unit_and_static_configuration(
    session: Session,
) -> None:
    instructor_id = persist_instructor(session)
    repository = SqlAlchemyAssignmentRepository(session)
    assignment = make_complete_assignment(instructor_id)
    repository.save(assignment)
    session.commit()

    assignment.set_unit_test_spec(
        instructor_id=instructor_id,
        specification=UnitTestSpecification(
            name="replacement tests",
            test_code="assert solve(1, 1) == 2",
            points=25,
        ),
    )
    assignment.set_static_analysis_rules(
        instructor_id=instructor_id,
        rules=StaticAnalysisRules(
            required_functions=("solve", "parse"),
            points=15,
        ),
    )

    repository.save(assignment)
    session.commit()
    session.expire_all()

    loaded = repository.get_by_id(assignment.id)  # type: ignore[arg-type]

    assert loaded is not None
    assert loaded.unit_test_spec is not None
    assert loaded.unit_test_spec.name == "replacement tests"
    assert loaded.static_analysis_rules is not None
    assert loaded.static_analysis_rules.required_functions == (
        "solve",
        "parse",
    )


def test_missing_persisted_assignment_cannot_be_updated(
    session: Session,
) -> None:
    instructor_id = persist_instructor(session)
    repository = SqlAlchemyAssignmentRepository(session)
    assignment = make_complete_assignment(instructor_id)
    assignment.id = 999

    with pytest.raises(AssignmentPersistenceError):
        repository.save(assignment)


def test_database_rejects_invalid_grading_weight_total(
    session: Session,
) -> None:
    instructor_id = persist_instructor(session)
    model = AssignmentModel(
        instructor_id=instructor_id,
        title="Invalid raw persistence state",
        description="Bypasses the domain on purpose.",
        language="python",
        status="draft",
        io_weight=70,
        unit_weight=20,
        static_weight=20,
        max_runtime_ms=2_000,
        max_memory_kb=128_000,
    )
    session.add(model)

    with pytest.raises(IntegrityError):
        session.flush()

    session.rollback()
