from __future__ import annotations

from dataclasses import dataclass

from app.domain.assessment import (
    Assignment,
    AssignmentStatus,
    GradingTestVisibility,
)


@dataclass(frozen=True, slots=True)
class IOTestView:
    id: int | None
    name: str
    stdin: str | None
    expected_stdout: str
    points: int
    visibility: GradingTestVisibility
    order_index: int


@dataclass(frozen=True, slots=True)
class UnitTestView:
    id: int | None
    name: str
    test_code: str
    points: int
    visibility: GradingTestVisibility


@dataclass(frozen=True, slots=True)
class StaticRulesView:
    id: int | None
    required_functions: tuple[str, ...]
    forbidden_imports: tuple[str, ...]
    max_cyclomatic_complexity: int | None
    points: int


@dataclass(frozen=True, slots=True)
class InstructorAssignmentView:
    id: int
    instructor_id: int
    title: str
    description: str
    instructions: str | None
    language: str
    status: AssignmentStatus
    io_weight: int
    unit_weight: int
    static_weight: int
    max_runtime_ms: int
    max_memory_kb: int
    io_test_cases: tuple[IOTestView, ...]
    unit_test_spec: UnitTestView | None
    static_analysis_rules: StaticRulesView | None

    @classmethod
    def from_domain(cls, assignment: Assignment) -> "InstructorAssignmentView":
        if assignment.id is None:
            raise ValueError("A persisted assignment id is required.")

        return cls(
            id=assignment.id,
            instructor_id=assignment.instructor_id,
            title=assignment.title,
            description=assignment.description,
            instructions=assignment.instructions,
            language=assignment.language,
            status=assignment.status,
            io_weight=assignment.grading_policy.io_weight,
            unit_weight=assignment.grading_policy.unit_weight,
            static_weight=assignment.grading_policy.static_weight,
            max_runtime_ms=assignment.execution_limits.max_runtime_ms,
            max_memory_kb=assignment.execution_limits.max_memory_kb,
            io_test_cases=tuple(
                IOTestView(
                    id=test.id,
                    name=test.name,
                    stdin=test.stdin,
                    expected_stdout=test.expected_stdout,
                    points=test.points,
                    visibility=test.visibility,
                    order_index=test.order_index,
                )
                for test in assignment.ordered_io_test_cases
            ),
            unit_test_spec=(
                UnitTestView(
                    id=assignment.unit_test_spec.id,
                    name=assignment.unit_test_spec.name,
                    test_code=assignment.unit_test_spec.test_code,
                    points=assignment.unit_test_spec.points,
                    visibility=assignment.unit_test_spec.visibility,
                )
                if assignment.unit_test_spec is not None
                else None
            ),
            static_analysis_rules=(
                StaticRulesView(
                    id=assignment.static_analysis_rules.id,
                    required_functions=(
                        assignment.static_analysis_rules.required_functions
                    ),
                    forbidden_imports=(
                        assignment.static_analysis_rules.forbidden_imports
                    ),
                    max_cyclomatic_complexity=(
                        assignment.static_analysis_rules
                        .max_cyclomatic_complexity
                    ),
                    points=assignment.static_analysis_rules.points,
                )
                if assignment.static_analysis_rules is not None
                else None
            ),
        )


@dataclass(frozen=True, slots=True)
class PublishedIOExample:
    name: str
    stdin: str | None
    expected_stdout: str
    points: int
    order_index: int


@dataclass(frozen=True, slots=True)
class PublishedUnitExample:
    name: str
    test_code: str
    points: int


@dataclass(frozen=True, slots=True)
class PublishedAssignmentView:
    id: int
    title: str
    description: str
    instructions: str | None
    language: str
    io_weight: int
    unit_weight: int
    static_weight: int
    max_runtime_ms: int
    max_memory_kb: int
    visible_io_examples: tuple[PublishedIOExample, ...]
    visible_unit_test: PublishedUnitExample | None
    required_functions: tuple[str, ...]
    forbidden_imports: tuple[str, ...]
    max_cyclomatic_complexity: int | None

    @classmethod
    def from_domain(cls, assignment: Assignment) -> "PublishedAssignmentView":
        if assignment.id is None:
            raise ValueError("A persisted assignment id is required.")

        if not assignment.is_published:
            raise ValueError("Only published assignments may be exposed.")

        visible_io = tuple(
            PublishedIOExample(
                name=test.name,
                stdin=test.stdin,
                expected_stdout=test.expected_stdout,
                points=test.points,
                order_index=test.order_index,
            )
            for test in assignment.ordered_io_test_cases
            if test.visibility is GradingTestVisibility.VISIBLE
        )

        visible_unit = None
        if (
            assignment.unit_test_spec is not None
            and assignment.unit_test_spec.visibility
            is GradingTestVisibility.VISIBLE
        ):
            visible_unit = PublishedUnitExample(
                name=assignment.unit_test_spec.name,
                test_code=assignment.unit_test_spec.test_code,
                points=assignment.unit_test_spec.points,
            )

        static_rules = assignment.static_analysis_rules

        return cls(
            id=assignment.id,
            title=assignment.title,
            description=assignment.description,
            instructions=assignment.instructions,
            language=assignment.language,
            io_weight=assignment.grading_policy.io_weight,
            unit_weight=assignment.grading_policy.unit_weight,
            static_weight=assignment.grading_policy.static_weight,
            max_runtime_ms=assignment.execution_limits.max_runtime_ms,
            max_memory_kb=assignment.execution_limits.max_memory_kb,
            visible_io_examples=visible_io,
            visible_unit_test=visible_unit,
            required_functions=(
                static_rules.required_functions if static_rules else ()
            ),
            forbidden_imports=(
                static_rules.forbidden_imports if static_rules else ()
            ),
            max_cyclomatic_complexity=(
                static_rules.max_cyclomatic_complexity
                if static_rules
                else None
            ),
        )
