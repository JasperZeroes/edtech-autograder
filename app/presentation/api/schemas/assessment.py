from __future__ import annotations

from pydantic import BaseModel, Field

from app.application.assessment.dto import (
    InstructorAssignmentView,
    PublishedAssignmentView,
)
from app.domain.assessment import (
    AssignmentStatus,
    ExecutionLimits,
    GradingPolicy,
    GradingTestVisibility,
    IOTestCase,
    StaticAnalysisRules,
    UnitTestSpecification,
)


class GradingPolicyRequest(BaseModel):
    io_weight: int = Field(default=70, ge=0, le=100)
    unit_weight: int = Field(default=20, ge=0, le=100)
    static_weight: int = Field(default=10, ge=0, le=100)

    def to_domain(self) -> GradingPolicy:
        return GradingPolicy(
            io_weight=self.io_weight,
            unit_weight=self.unit_weight,
            static_weight=self.static_weight,
        )


class ExecutionLimitsRequest(BaseModel):
    max_runtime_ms: int = Field(default=2_000, ge=100, le=600_000)
    max_memory_kb: int = Field(default=128_000, ge=16_000, le=2_000_000)

    def to_domain(self) -> ExecutionLimits:
        return ExecutionLimits(
            max_runtime_ms=self.max_runtime_ms,
            max_memory_kb=self.max_memory_kb,
        )


class IOTestCaseRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    expected_stdout: str = Field(min_length=1)
    stdin: str | None = None
    points: int = Field(default=1, ge=0, le=100_000)
    visibility: GradingTestVisibility = GradingTestVisibility.HIDDEN
    order_index: int = Field(default=0, ge=0)

    def to_domain(self) -> IOTestCase:
        return IOTestCase(
            name=self.name,
            expected_stdout=self.expected_stdout,
            stdin=self.stdin,
            points=self.points,
            visibility=self.visibility,
            order_index=self.order_index,
        )


class UnitTestSpecificationRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    test_code: str = Field(min_length=1)
    points: int = Field(default=0, ge=0, le=100_000)
    visibility: GradingTestVisibility = GradingTestVisibility.HIDDEN

    def to_domain(self) -> UnitTestSpecification:
        return UnitTestSpecification(
            name=self.name,
            test_code=self.test_code,
            points=self.points,
            visibility=self.visibility,
        )


class StaticAnalysisRulesRequest(BaseModel):
    required_functions: list[str] = Field(default_factory=list)
    forbidden_imports: list[str] = Field(default_factory=list)
    max_cyclomatic_complexity: int | None = Field(
        default=None,
        ge=1,
        le=10_000,
    )
    points: int = Field(default=0, ge=0, le=100_000)

    def to_domain(self) -> StaticAnalysisRules:
        return StaticAnalysisRules(
            required_functions=tuple(self.required_functions),
            forbidden_imports=tuple(self.forbidden_imports),
            max_cyclomatic_complexity=self.max_cyclomatic_complexity,
            points=self.points,
        )


class CreateAssignmentRequest(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    description: str = Field(min_length=1)
    instructions: str | None = None
    grading_policy: GradingPolicyRequest | None = None
    execution_limits: ExecutionLimitsRequest | None = None


class ConfigureAssignmentRequest(BaseModel):
    grading_policy: GradingPolicyRequest | None = None
    execution_limits: ExecutionLimitsRequest | None = None
    io_test_cases: list[IOTestCaseRequest] = Field(default_factory=list)
    unit_test_spec: UnitTestSpecificationRequest | None = None
    static_analysis_rules: StaticAnalysisRulesRequest | None = None


class IOTestResponse(BaseModel):
    id: int | None
    name: str
    stdin: str | None
    expected_stdout: str
    points: int
    visibility: GradingTestVisibility
    order_index: int


class UnitTestResponse(BaseModel):
    id: int | None
    name: str
    test_code: str
    points: int
    visibility: GradingTestVisibility


class StaticRulesResponse(BaseModel):
    id: int | None
    required_functions: tuple[str, ...]
    forbidden_imports: tuple[str, ...]
    max_cyclomatic_complexity: int | None
    points: int


class InstructorAssignmentResponse(BaseModel):
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
    io_test_cases: tuple[IOTestResponse, ...]
    unit_test_spec: UnitTestResponse | None
    static_analysis_rules: StaticRulesResponse | None

    @classmethod
    def from_view(
        cls,
        view: InstructorAssignmentView,
    ) -> "InstructorAssignmentResponse":
        return cls(
            id=view.id,
            instructor_id=view.instructor_id,
            title=view.title,
            description=view.description,
            instructions=view.instructions,
            language=view.language,
            status=view.status,
            io_weight=view.io_weight,
            unit_weight=view.unit_weight,
            static_weight=view.static_weight,
            max_runtime_ms=view.max_runtime_ms,
            max_memory_kb=view.max_memory_kb,
            io_test_cases=tuple(
                IOTestResponse(
                    id=test.id,
                    name=test.name,
                    stdin=test.stdin,
                    expected_stdout=test.expected_stdout,
                    points=test.points,
                    visibility=test.visibility,
                    order_index=test.order_index,
                )
                for test in view.io_test_cases
            ),
            unit_test_spec=(
                UnitTestResponse(
                    id=view.unit_test_spec.id,
                    name=view.unit_test_spec.name,
                    test_code=view.unit_test_spec.test_code,
                    points=view.unit_test_spec.points,
                    visibility=view.unit_test_spec.visibility,
                )
                if view.unit_test_spec is not None
                else None
            ),
            static_analysis_rules=(
                StaticRulesResponse(
                    id=view.static_analysis_rules.id,
                    required_functions=view.static_analysis_rules.required_functions,
                    forbidden_imports=view.static_analysis_rules.forbidden_imports,
                    max_cyclomatic_complexity=(
                        view.static_analysis_rules.max_cyclomatic_complexity
                    ),
                    points=view.static_analysis_rules.points,
                )
                if view.static_analysis_rules is not None
                else None
            ),
        )


class PublishedIOExampleResponse(BaseModel):
    name: str
    stdin: str | None
    expected_stdout: str
    points: int
    order_index: int


class PublishedUnitExampleResponse(BaseModel):
    name: str
    test_code: str
    points: int


class PublishedAssignmentResponse(BaseModel):
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
    visible_io_examples: tuple[PublishedIOExampleResponse, ...]
    visible_unit_test: PublishedUnitExampleResponse | None
    required_functions: tuple[str, ...]
    forbidden_imports: tuple[str, ...]
    max_cyclomatic_complexity: int | None

    @classmethod
    def from_view(
        cls,
        view: PublishedAssignmentView,
    ) -> "PublishedAssignmentResponse":
        return cls(
            id=view.id,
            title=view.title,
            description=view.description,
            instructions=view.instructions,
            language=view.language,
            io_weight=view.io_weight,
            unit_weight=view.unit_weight,
            static_weight=view.static_weight,
            max_runtime_ms=view.max_runtime_ms,
            max_memory_kb=view.max_memory_kb,
            visible_io_examples=tuple(
                PublishedIOExampleResponse(
                    name=test.name,
                    stdin=test.stdin,
                    expected_stdout=test.expected_stdout,
                    points=test.points,
                    order_index=test.order_index,
                )
                for test in view.visible_io_examples
            ),
            visible_unit_test=(
                PublishedUnitExampleResponse(
                    name=view.visible_unit_test.name,
                    test_code=view.visible_unit_test.test_code,
                    points=view.visible_unit_test.points,
                )
                if view.visible_unit_test is not None
                else None
            ),
            required_functions=view.required_functions,
            forbidden_imports=view.forbidden_imports,
            max_cyclomatic_complexity=view.max_cyclomatic_complexity,
        )
