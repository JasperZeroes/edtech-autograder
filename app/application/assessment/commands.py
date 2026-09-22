from __future__ import annotations

from dataclasses import dataclass

from app.domain.assessment import (
    ExecutionLimits,
    GradingPolicy,
    IOTestCase,
    StaticAnalysisRules,
    UnitTestSpecification,
)


@dataclass(frozen=True, slots=True)
class CreateAssignmentCommand:
    instructor_id: int
    title: str
    description: str
    instructions: str | None = None
    grading_policy: GradingPolicy | None = None
    execution_limits: ExecutionLimits | None = None


@dataclass(frozen=True, slots=True)
class ConfigureAssignmentCommand:
    assignment_id: int
    instructor_id: int
    grading_policy: GradingPolicy | None = None
    execution_limits: ExecutionLimits | None = None
    io_test_cases: tuple[IOTestCase, ...] = ()
    unit_test_spec: UnitTestSpecification | None = None
    static_analysis_rules: StaticAnalysisRules | None = None


@dataclass(frozen=True, slots=True)
class PublishAssignmentCommand:
    assignment_id: int
    instructor_id: int


@dataclass(frozen=True, slots=True)
class UnpublishAssignmentCommand:
    assignment_id: int
    instructor_id: int
