import pytest

from app.domain.assessment import (
    AssessmentValidationError,
    Assignment,
    AssignmentNotReadyError,
    AssignmentOwnershipError,
    AssignmentStatus,
    ExecutionLimits,
    GradingPolicy,
    IOTestCase,
    StaticAnalysisRules,
    UnitTestSpecification,
)


def make_assignment(
    *,
    policy: GradingPolicy | None = None,
) -> Assignment:
    return Assignment.create(
        instructor_id=7,
        title="  Functions and Control Flow  ",
        description="  Implement the required Python functions.  ",
        instructions="  Submit one Python file.  ",
        grading_policy=policy,
    )


def configure_all_grading_components(assignment: Assignment) -> None:
    assignment.add_io_test_case(
        instructor_id=7,
        test_case=IOTestCase(
            name="basic case",
            stdin="2 3",
            expected_stdout="5",
            points=10,
        ),
    )
    assignment.set_unit_test_spec(
        instructor_id=7,
        specification=UnitTestSpecification(
            name="function tests",
            test_code="assert solve(2, 3) == 5",
            points=10,
        ),
    )
    assignment.set_static_analysis_rules(
        instructor_id=7,
        rules=StaticAnalysisRules(
            required_functions=("solve",),
            max_cyclomatic_complexity=10,
            points=10,
        ),
    )


def test_create_assignment_starts_as_normalized_draft() -> None:
    assignment = make_assignment()

    assert assignment.id is None
    assert assignment.instructor_id == 7
    assert assignment.title == "Functions and Control Flow"
    assert assignment.description == "Implement the required Python functions."
    assert assignment.instructions == "Submit one Python file."
    assert assignment.language == "python"
    assert assignment.status is AssignmentStatus.DRAFT
    assert assignment.is_published is False
    assert assignment.grading_policy == GradingPolicy()
    assert assignment.execution_limits == ExecutionLimits()


@pytest.mark.parametrize(
    "overrides",
    [
        {"instructor_id": 0},
        {"title": "ab"},
        {"description": "   "},
    ],
)
def test_invalid_assignment_identity_or_content_is_rejected(
    overrides: dict[str, object],
) -> None:
    values: dict[str, object] = {
        "instructor_id": 7,
        "title": "Valid title",
        "description": "Valid description",
    }
    values.update(overrides)

    with pytest.raises(AssessmentValidationError):
        Assignment.create(**values)  # type: ignore[arg-type]


def test_phase_one_rejects_non_python_assignment() -> None:
    with pytest.raises(
        AssessmentValidationError,
        match="supports Python assignments only",
    ):
        Assignment(
            id=None,
            instructor_id=7,
            title="Java exercise",
            description="Implement this task.",
            language="java",
        )


def test_non_owner_cannot_configure_assignment() -> None:
    assignment = make_assignment()

    with pytest.raises(AssignmentOwnershipError):
        assignment.configure_execution_limits(
            instructor_id=99,
            limits=ExecutionLimits(max_runtime_ms=5_000),
        )


def test_owner_can_configure_assessment_components() -> None:
    assignment = make_assignment()
    configure_all_grading_components(assignment)

    assignment.configure_execution_limits(
        instructor_id=7,
        limits=ExecutionLimits(
            max_runtime_ms=5_000,
            max_memory_kb=256_000,
        ),
    )

    assert len(assignment.io_test_cases) == 1
    assert assignment.unit_test_spec is not None
    assert assignment.static_analysis_rules is not None
    assert assignment.execution_limits.max_runtime_ms == 5_000


def test_io_test_cases_are_exposed_in_evaluation_order() -> None:
    assignment = make_assignment(
        policy=GradingPolicy(
            io_weight=100,
            unit_weight=0,
            static_weight=0,
        )
    )
    assignment.add_io_test_case(
        instructor_id=7,
        test_case=IOTestCase(
            id=2,
            name="second",
            expected_stdout="2",
            order_index=2,
        ),
    )
    assignment.add_io_test_case(
        instructor_id=7,
        test_case=IOTestCase(
            id=1,
            name="first",
            expected_stdout="1",
            order_index=1,
        ),
    )

    assert [test.name for test in assignment.ordered_io_test_cases] == [
        "first",
        "second",
    ]


def test_default_policy_cannot_publish_without_io_tests() -> None:
    assignment = make_assignment()
    assignment.set_unit_test_spec(
        instructor_id=7,
        specification=UnitTestSpecification(
            name="unit tests",
            test_code="assert True",
            points=20,
        ),
    )
    assignment.set_static_analysis_rules(
        instructor_id=7,
        rules=StaticAnalysisRules(
            required_functions=("solve",),
            points=10,
        ),
    )

    with pytest.raises(AssignmentNotReadyError, match="IO test cases"):
        assignment.publish(instructor_id=7)


def test_default_policy_cannot_publish_without_unit_tests() -> None:
    assignment = make_assignment()
    assignment.add_io_test_case(
        instructor_id=7,
        test_case=IOTestCase(
            name="io",
            expected_stdout="ok",
            points=70,
        ),
    )
    assignment.set_static_analysis_rules(
        instructor_id=7,
        rules=StaticAnalysisRules(
            required_functions=("solve",),
            points=10,
        ),
    )

    with pytest.raises(
        AssignmentNotReadyError,
        match="unit-test specification",
    ):
        assignment.publish(instructor_id=7)


def test_default_policy_cannot_publish_without_static_rules() -> None:
    assignment = make_assignment()
    assignment.add_io_test_case(
        instructor_id=7,
        test_case=IOTestCase(
            name="io",
            expected_stdout="ok",
            points=70,
        ),
    )
    assignment.set_unit_test_spec(
        instructor_id=7,
        specification=UnitTestSpecification(
            name="unit",
            test_code="assert True",
            points=20,
        ),
    )

    with pytest.raises(
        AssignmentNotReadyError,
        match="static-analysis rules",
    ):
        assignment.publish(instructor_id=7)


def test_weighted_component_requires_positive_points() -> None:
    assignment = make_assignment(
        policy=GradingPolicy(
            io_weight=100,
            unit_weight=0,
            static_weight=0,
        )
    )
    assignment.add_io_test_case(
        instructor_id=7,
        test_case=IOTestCase(
            name="zero point test",
            expected_stdout="ok",
            points=0,
        ),
    )

    with pytest.raises(
        AssignmentNotReadyError,
        match="positive IO test points",
    ):
        assignment.publish(instructor_id=7)


def test_zero_weight_components_are_not_required_for_publication() -> None:
    assignment = make_assignment(
        policy=GradingPolicy(
            io_weight=100,
            unit_weight=0,
            static_weight=0,
        )
    )
    assignment.add_io_test_case(
        instructor_id=7,
        test_case=IOTestCase(
            name="only grading mechanism",
            expected_stdout="ok",
            points=100,
        ),
    )

    assignment.publish(instructor_id=7)

    assert assignment.is_published is True


def test_fully_configured_assignment_can_be_published_and_unpublished() -> None:
    assignment = make_assignment()
    configure_all_grading_components(assignment)

    assignment.publish(instructor_id=7)
    assert assignment.status is AssignmentStatus.PUBLISHED

    assignment.unpublish(instructor_id=7)
    assert assignment.status is AssignmentStatus.DRAFT


def test_publish_is_idempotent() -> None:
    assignment = make_assignment()
    configure_all_grading_components(assignment)

    assignment.publish(instructor_id=7)
    assignment.publish(instructor_id=7)

    assert assignment.is_published is True


def test_non_owner_cannot_publish_or_unpublish() -> None:
    assignment = make_assignment()
    configure_all_grading_components(assignment)

    with pytest.raises(AssignmentOwnershipError):
        assignment.publish(instructor_id=99)

    assignment.publish(instructor_id=7)

    with pytest.raises(AssignmentOwnershipError):
        assignment.unpublish(instructor_id=99)


def test_published_assignment_cannot_adopt_policy_it_cannot_satisfy() -> None:
    assignment = make_assignment(
        policy=GradingPolicy(
            io_weight=100,
            unit_weight=0,
            static_weight=0,
        )
    )
    assignment.add_io_test_case(
        instructor_id=7,
        test_case=IOTestCase(
            name="io",
            expected_stdout="ok",
            points=100,
        ),
    )
    assignment.publish(instructor_id=7)

    original_policy = assignment.grading_policy

    with pytest.raises(
        AssignmentNotReadyError,
        match="unit-test specification",
    ):
        assignment.configure_grading_policy(
            instructor_id=7,
            policy=GradingPolicy(
                io_weight=80,
                unit_weight=20,
                static_weight=0,
            ),
        )

    assert assignment.grading_policy == original_policy
