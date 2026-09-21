from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .errors import (
    AssessmentValidationError,
    AssignmentNotReadyError,
    AssignmentOwnershipError,
)
from .execution_limits import ExecutionLimits
from .grading_policy import GradingPolicy
from .evaluation_rules import (
    IOTestCase,
    StaticAnalysisRules,
    UnitTestSpecification,
)


class AssignmentStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"


@dataclass(slots=True)
class Assignment:
    """Aggregate root for instructor-authored programming assessments."""

    id: int | None
    instructor_id: int
    title: str
    description: str
    instructions: str | None = None
    language: str = "python"
    status: AssignmentStatus = AssignmentStatus.DRAFT
    grading_policy: GradingPolicy = field(default_factory=GradingPolicy)
    execution_limits: ExecutionLimits = field(default_factory=ExecutionLimits)
    io_test_cases: list[IOTestCase] = field(default_factory=list)
    unit_test_spec: UnitTestSpecification | None = None
    static_analysis_rules: StaticAnalysisRules | None = None

    def __post_init__(self) -> None:
        if self.id is not None and self.id <= 0:
            raise AssessmentValidationError(
                "Assignment id must be a positive integer."
            )

        if self.instructor_id <= 0:
            raise AssessmentValidationError(
                "Instructor id must be a positive integer."
            )

        title = self.title.strip()
        if not 3 <= len(title) <= 255:
            raise AssessmentValidationError(
                "Assignment title must contain between 3 and 255 characters."
            )
        self.title = title

        description = self.description.strip()
        if not description:
            raise AssessmentValidationError(
                "Assignment description must not be empty."
            )
        self.description = description

        if self.instructions is not None:
            normalized_instructions = self.instructions.strip()
            self.instructions = normalized_instructions or None

        language = self.language.strip().lower()
        if language != "python":
            raise AssessmentValidationError(
                "Phase 1 supports Python assignments only."
            )
        self.language = language

        if not isinstance(self.status, AssignmentStatus):
            try:
                self.status = AssignmentStatus(self.status)
            except ValueError as exc:
                raise AssessmentValidationError(
                    "Assignment status must be 'draft' or 'published'."
                ) from exc

        if self.status is AssignmentStatus.PUBLISHED:
            self._assert_ready_to_publish()

    @classmethod
    def create(
        cls,
        *,
        instructor_id: int,
        title: str,
        description: str,
        instructions: str | None = None,
        grading_policy: GradingPolicy | None = None,
        execution_limits: ExecutionLimits | None = None,
    ) -> "Assignment":
        return cls(
            id=None,
            instructor_id=instructor_id,
            title=title,
            description=description,
            instructions=instructions,
            grading_policy=grading_policy or GradingPolicy(),
            execution_limits=execution_limits or ExecutionLimits(),
        )

    @property
    def is_published(self) -> bool:
        return self.status is AssignmentStatus.PUBLISHED

    @property
    def ordered_io_test_cases(self) -> tuple[IOTestCase, ...]:
        return tuple(
            sorted(
                self.io_test_cases,
                key=lambda test: (test.order_index, test.id or 0),
            )
        )

    def assert_owned_by(self, instructor_id: int) -> None:
        if instructor_id != self.instructor_id:
            raise AssignmentOwnershipError(
                "Only the owning instructor may modify this assignment."
            )

    def configure_grading_policy(
        self,
        *,
        instructor_id: int,
        policy: GradingPolicy,
    ) -> None:
        self.assert_owned_by(instructor_id)

        if self.is_published:
            self._assert_ready_to_publish(policy=policy)

        self.grading_policy = policy

    def configure_execution_limits(
        self,
        *,
        instructor_id: int,
        limits: ExecutionLimits,
    ) -> None:
        self.assert_owned_by(instructor_id)
        self.execution_limits = limits

    def add_io_test_case(
        self,
        *,
        instructor_id: int,
        test_case: IOTestCase,
    ) -> None:
        self.assert_owned_by(instructor_id)
        self.io_test_cases.append(test_case)

    def set_unit_test_spec(
        self,
        *,
        instructor_id: int,
        specification: UnitTestSpecification,
    ) -> None:
        self.assert_owned_by(instructor_id)
        self.unit_test_spec = specification

    def set_static_analysis_rules(
        self,
        *,
        instructor_id: int,
        rules: StaticAnalysisRules,
    ) -> None:
        self.assert_owned_by(instructor_id)
        self.static_analysis_rules = rules

    def publish(self, *, instructor_id: int) -> None:
        self.assert_owned_by(instructor_id)

        if self.is_published:
            return

        self._assert_ready_to_publish()
        self.status = AssignmentStatus.PUBLISHED

    def unpublish(self, *, instructor_id: int) -> None:
        self.assert_owned_by(instructor_id)
        self.status = AssignmentStatus.DRAFT

    def _assert_ready_to_publish(
        self,
        *,
        policy: GradingPolicy | None = None,
    ) -> None:
        active_policy = policy or self.grading_policy
        missing: list[str] = []

        if active_policy.io_weight > 0:
            if not self.io_test_cases:
                missing.append("IO test cases")
            elif sum(test.points for test in self.io_test_cases) <= 0:
                missing.append("positive IO test points")

        if active_policy.unit_weight > 0:
            if self.unit_test_spec is None:
                missing.append("unit-test specification")
            elif self.unit_test_spec.points <= 0:
                missing.append("positive unit-test points")

        if active_policy.static_weight > 0:
            rules = self.static_analysis_rules
            if rules is None or not rules.has_checks:
                missing.append("static-analysis rules")
            elif rules.points <= 0:
                missing.append("positive static-analysis points")

        if missing:
            raise AssignmentNotReadyError(
                "Assignment is not ready to publish; missing: "
                + ", ".join(missing)
                + "."
            )
