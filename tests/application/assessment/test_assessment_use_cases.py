import pytest

from app.application.assessment import (
    AssignmentNotFoundError,
    ConfigureAssignment,
    ConfigureAssignmentCommand,
    CreateAssignment,
    CreateAssignmentCommand,
    GetInstructorAssignment,
    GetPublishedAssignment,
    ListInstructorAssignments,
    ListPublishedAssignments,
    PublishAssignment,
    PublishAssignmentCommand,
    PublishedAssignmentNotFoundError,
    UnpublishAssignment,
    UnpublishAssignmentCommand,
)
from app.domain.assessment import (
    Assignment,
    AssignmentNotReadyError,
    AssignmentOwnershipError,
    AssignmentStatus,
    ExecutionLimits,
    GradingPolicy,
    GradingTestVisibility,
    IOTestCase,
    StaticAnalysisRules,
    UnitTestSpecification,
)

from .fakes import FakeAssessmentUnitOfWork


def make_assignment(
    *,
    instructor_id: int = 7,
    title: str = "Functions and Control Flow",
    published: bool = False,
) -> Assignment:
    assignment = Assignment.create(
        instructor_id=instructor_id,
        title=title,
        description="Implement the required Python functions.",
    )

    if published:
        configure_complete_assignment(assignment)
        assignment.publish(instructor_id=instructor_id)

    return assignment


def configure_complete_assignment(assignment: Assignment) -> None:
    owner = assignment.instructor_id

    assignment.add_io_test_case(
        instructor_id=owner,
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
        instructor_id=owner,
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
        instructor_id=owner,
        specification=UnitTestSpecification(
            name="hidden unit tests",
            test_code="assert solve(2, 3) == 5",
            points=20,
            visibility=GradingTestVisibility.HIDDEN,
        ),
    )
    assignment.set_static_analysis_rules(
        instructor_id=owner,
        rules=StaticAnalysisRules(
            required_functions=("solve",),
            forbidden_imports=("os",),
            max_cyclomatic_complexity=10,
            points=10,
        ),
    )


def test_create_assignment_persists_and_commits() -> None:
    unit_of_work = FakeAssessmentUnitOfWork()
    use_case = CreateAssignment(unit_of_work=unit_of_work)

    result = use_case.execute(
        CreateAssignmentCommand(
            instructor_id=7,
            title="  Functions and Control Flow  ",
            description="Build a Python solution.",
            instructions="Submit one file.",
            grading_policy=GradingPolicy(
                io_weight=100,
                unit_weight=0,
                static_weight=0,
            ),
            execution_limits=ExecutionLimits(
                max_runtime_ms=5_000,
                max_memory_kb=256_000,
            ),
        )
    )

    assert result.id == 1
    assert result.instructor_id == 7
    assert result.title == "Functions and Control Flow"
    assert result.status is AssignmentStatus.DRAFT
    assert result.io_weight == 100
    assert result.max_runtime_ms == 5_000
    assert unit_of_work.committed is True
    assert unit_of_work.rolled_back is False


def test_create_assignment_rolls_back_when_persistence_fails() -> None:
    unit_of_work = FakeAssessmentUnitOfWork()
    unit_of_work.assignments.fail_on_save = True
    use_case = CreateAssignment(unit_of_work=unit_of_work)

    with pytest.raises(RuntimeError, match="persistence failed"):
        use_case.execute(
            CreateAssignmentCommand(
                instructor_id=7,
                title="Valid Assignment",
                description="Valid description.",
            )
        )

    assert unit_of_work.committed is False
    assert unit_of_work.rolled_back is True


def test_configure_assignment_adds_grading_configuration() -> None:
    assignment = make_assignment()
    unit_of_work = FakeAssessmentUnitOfWork([assignment])
    use_case = ConfigureAssignment(unit_of_work=unit_of_work)

    result = use_case.execute(
        ConfigureAssignmentCommand(
            assignment_id=assignment.id,  # type: ignore[arg-type]
            instructor_id=7,
            grading_policy=GradingPolicy(
                io_weight=80,
                unit_weight=20,
                static_weight=0,
            ),
            execution_limits=ExecutionLimits(
                max_runtime_ms=4_000,
                max_memory_kb=256_000,
            ),
            io_test_cases=(
                IOTestCase(
                    name="basic case",
                    expected_stdout="5",
                    points=80,
                ),
            ),
            unit_test_spec=UnitTestSpecification(
                name="unit checks",
                test_code="assert solve(2, 3) == 5",
                points=20,
            ),
        )
    )

    assert result.io_weight == 80
    assert result.unit_weight == 20
    assert result.static_weight == 0
    assert result.max_runtime_ms == 4_000
    assert len(result.io_test_cases) == 1
    assert result.unit_test_spec is not None
    assert unit_of_work.committed is True


def test_configure_assignment_rejects_non_owner() -> None:
    assignment = make_assignment()
    unit_of_work = FakeAssessmentUnitOfWork([assignment])

    with pytest.raises(AssignmentOwnershipError):
        ConfigureAssignment(unit_of_work=unit_of_work).execute(
            ConfigureAssignmentCommand(
                assignment_id=assignment.id,  # type: ignore[arg-type]
                instructor_id=99,
                execution_limits=ExecutionLimits(max_runtime_ms=3_000),
            )
        )

    assert unit_of_work.committed is False


def test_configure_missing_assignment_raises_application_error() -> None:
    unit_of_work = FakeAssessmentUnitOfWork()

    with pytest.raises(
        AssignmentNotFoundError,
        match="Assignment 999 was not found",
    ):
        ConfigureAssignment(unit_of_work=unit_of_work).execute(
            ConfigureAssignmentCommand(
                assignment_id=999,
                instructor_id=7,
            )
        )


def test_publish_assignment_persists_state_change() -> None:
    assignment = make_assignment()
    configure_complete_assignment(assignment)
    unit_of_work = FakeAssessmentUnitOfWork([assignment])

    result = PublishAssignment(unit_of_work=unit_of_work).execute(
        PublishAssignmentCommand(
            assignment_id=assignment.id,  # type: ignore[arg-type]
            instructor_id=7,
        )
    )

    assert result.status is AssignmentStatus.PUBLISHED
    assert unit_of_work.committed is True


def test_publish_propagates_domain_readiness_error() -> None:
    assignment = make_assignment()
    unit_of_work = FakeAssessmentUnitOfWork([assignment])

    with pytest.raises(AssignmentNotReadyError):
        PublishAssignment(unit_of_work=unit_of_work).execute(
            PublishAssignmentCommand(
                assignment_id=assignment.id,  # type: ignore[arg-type]
                instructor_id=7,
            )
        )

    assert unit_of_work.committed is False


def test_unpublish_assignment_persists_state_change() -> None:
    assignment = make_assignment(published=True)
    unit_of_work = FakeAssessmentUnitOfWork([assignment])

    result = UnpublishAssignment(unit_of_work=unit_of_work).execute(
        UnpublishAssignmentCommand(
            assignment_id=assignment.id,  # type: ignore[arg-type]
            instructor_id=7,
        )
    )

    assert result.status is AssignmentStatus.DRAFT
    assert unit_of_work.committed is True


def test_get_instructor_assignment_enforces_ownership() -> None:
    assignment = make_assignment()
    unit_of_work = FakeAssessmentUnitOfWork([assignment])
    use_case = GetInstructorAssignment(unit_of_work=unit_of_work)

    result = use_case.execute(
        assignment_id=assignment.id,  # type: ignore[arg-type]
        instructor_id=7,
    )
    assert result.id == assignment.id

    with pytest.raises(AssignmentOwnershipError):
        use_case.execute(
            assignment_id=assignment.id,  # type: ignore[arg-type]
            instructor_id=99,
        )


def test_list_instructor_assignments_returns_only_owned_records() -> None:
    first = make_assignment(instructor_id=7, title="First Assignment")
    second = make_assignment(instructor_id=8, title="Other Assignment")
    third = make_assignment(instructor_id=7, title="Second Assignment")

    unit_of_work = FakeAssessmentUnitOfWork([first, second, third])

    results = ListInstructorAssignments(
        unit_of_work=unit_of_work
    ).execute(instructor_id=7)

    assert [result.title for result in results] == [
        "First Assignment",
        "Second Assignment",
    ]


def test_list_published_assignments_excludes_drafts() -> None:
    draft = make_assignment(title="Draft Assignment")
    published = make_assignment(
        title="Published Assignment",
        published=True,
    )
    unit_of_work = FakeAssessmentUnitOfWork([draft, published])

    results = ListPublishedAssignments(
        unit_of_work=unit_of_work
    ).execute()

    assert [result.title for result in results] == ["Published Assignment"]


def test_student_view_hides_hidden_grading_tests() -> None:
    assignment = make_assignment()
    configure_complete_assignment(assignment)

    assignment.set_unit_test_spec(
        instructor_id=7,
        specification=UnitTestSpecification(
            name="visible unit example",
            test_code="assert solve(1, 1) == 2",
            points=20,
            visibility=GradingTestVisibility.VISIBLE,
        ),
    )
    assignment.publish(instructor_id=7)

    unit_of_work = FakeAssessmentUnitOfWork([assignment])

    result = GetPublishedAssignment(
        unit_of_work=unit_of_work
    ).execute(assignment_id=assignment.id)  # type: ignore[arg-type]

    assert [test.name for test in result.visible_io_examples] == [
        "visible example"
    ]
    assert all(
        test.name != "hidden edge case"
        for test in result.visible_io_examples
    )
    assert result.visible_unit_test is not None
    assert result.visible_unit_test.name == "visible unit example"
    assert result.required_functions == ("solve",)
    assert result.forbidden_imports == ("os",)


def test_hidden_unit_test_code_is_not_exposed_to_student() -> None:
    assignment = make_assignment(published=True)
    unit_of_work = FakeAssessmentUnitOfWork([assignment])

    result = GetPublishedAssignment(
        unit_of_work=unit_of_work
    ).execute(assignment_id=assignment.id)  # type: ignore[arg-type]

    assert result.visible_unit_test is None
    assert [test.name for test in result.visible_io_examples] == [
        "visible example"
    ]


def test_get_published_assignment_treats_draft_as_not_found() -> None:
    draft = make_assignment()
    unit_of_work = FakeAssessmentUnitOfWork([draft])

    with pytest.raises(PublishedAssignmentNotFoundError):
        GetPublishedAssignment(
            unit_of_work=unit_of_work
        ).execute(assignment_id=draft.id)  # type: ignore[arg-type]
