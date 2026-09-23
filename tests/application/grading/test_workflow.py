from decimal import Decimal

import pytest

from app.application.grading import (
    CodeExecutionRequest,
    CodeExecutionUnavailableError,
    GradeSubmission,
    GradingAssignmentNotFoundError,
    GradingResultMissingError,
    GradingSubmissionNotFoundError,
    SourceAnalysisReport,
    SubmissionAlreadyRunningError,
)
from app.domain.assessment import (
    Assignment,
    GradingPolicy,
    GradingTestVisibility,
    IOTestCase,
    StaticAnalysisRules,
    UnitTestSpecification,
)
from app.domain.grading import (
    EvaluationStatus,
    ExecutionOutcome,
    StoredGradingResult,
)
from app.domain.submission import SourceCode, Submission, SubmissionStatus
from tests.application.assessment.fakes import FakeAssignmentRepository
from tests.application.submission.fakes import FakeSubmissionRepository


class FakeGradingResultRepository:
    def __init__(self) -> None:
        self._results: dict[int, StoredGradingResult] = {}
        self._next_id = 1

    def get_by_submission_id(
        self,
        submission_id: int,
    ) -> StoredGradingResult | None:
        return self._results.get(submission_id)

    def save(self, *, submission_id: int, result):
        stored = StoredGradingResult(
            id=self._next_id,
            submission_id=submission_id,
            result=result,
        )
        self._next_id += 1
        self._results[submission_id] = stored
        return stored


class FakeGradingUnitOfWork:
    def __init__(
        self,
        *,
        assignments: list[Assignment] | None = None,
        submissions: list[Submission] | None = None,
    ) -> None:
        self.assignments = FakeAssignmentRepository(assignments)
        self.submissions = FakeSubmissionRepository(submissions)
        self.grading_results = FakeGradingResultRepository()
        self.commits = 0
        self.rollbacks = 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


class FakeExecutionGateway:
    def __init__(
        self,
        outcomes: list[ExecutionOutcome] | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self.outcomes = list(outcomes or [])
        self.error = error
        self.requests: list[CodeExecutionRequest] = []

    def execute(self, request: CodeExecutionRequest) -> ExecutionOutcome:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        if not self.outcomes:
            raise AssertionError("No fake execution outcome configured.")
        return self.outcomes.pop(0)


class FakeSourceAnalyzer:
    def __init__(
        self,
        report: SourceAnalysisReport | None = None,
    ) -> None:
        self.report = report or SourceAnalysisReport(
            syntax_valid=True,
            missing_required_functions=(),
            forbidden_imports_found=(),
            observed_max_cyclomatic_complexity=1,
            max_cyclomatic_complexity_allowed=10,
        )
        self.calls: list[tuple[str, StaticAnalysisRules]] = []

    def analyze(
        self,
        *,
        source_code: str,
        rules: StaticAnalysisRules,
    ) -> SourceAnalysisReport:
        self.calls.append((source_code, rules))
        return self.report


def make_assignment() -> Assignment:
    assignment = Assignment.create(
        instructor_id=7,
        title="Functions and Control Flow",
        description="Implement solve().",
        grading_policy=GradingPolicy(
            io_weight=70,
            unit_weight=20,
            static_weight=10,
        ),
    )
    assignment.add_io_test_case(
        instructor_id=7,
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
        instructor_id=7,
        test_case=IOTestCase(
            name="hidden edge",
            stdin="-1 1",
            expected_stdout="0",
            points=30,
            visibility=GradingTestVisibility.HIDDEN,
            order_index=2,
        ),
    )
    assignment.set_unit_test_spec(
        instructor_id=7,
        specification=UnitTestSpecification(
            name="hidden unit tests",
            test_code="assert solve(2, 3) == 5",
            points=20,
            visibility=GradingTestVisibility.HIDDEN,
        ),
    )
    assignment.set_static_analysis_rules(
        instructor_id=7,
        rules=StaticAnalysisRules(
            required_functions=("solve",),
            forbidden_imports=("os",),
            max_cyclomatic_complexity=10,
            points=10,
        ),
    )
    assignment.publish(instructor_id=7)
    return assignment


def make_submission(assignment_id: int) -> Submission:
    return Submission(
        id=1,
        assignment_id=assignment_id,
        student_id=20,
        attempt_number=1,
        source_code=SourceCode(
            "def solve(a, b):\n"
            "    return a + b\n"
            "\n"
            "a, b = map(int, input().split())\n"
            "print(solve(a, b))\n"
        ),
        status=SubmissionStatus.QUEUED,
    )


def successful_execution(stdout: str = "") -> ExecutionOutcome:
    return ExecutionOutcome(
        status=EvaluationStatus.PASSED,
        stdout=stdout,
        runtime_ms=10,
    )


def build_workflow(
    *,
    gateway: FakeExecutionGateway,
    analyzer: FakeSourceAnalyzer | None = None,
):
    assignment = make_assignment()
    assert assignment.id is None
    assignments = FakeAssignmentRepository([assignment])
    assert assignment.id is not None
    submission = make_submission(assignment.id)
    uow = FakeGradingUnitOfWork(
        assignments=list(assignments._assignments.values()),
        submissions=[submission],
    )
    workflow = GradeSubmission(
        unit_of_work=uow,
        execution_gateway=gateway,
        source_analyzer=analyzer or FakeSourceAnalyzer(),
    )
    return workflow, uow, assignment, submission


def test_successful_workflow_persists_weighted_result_and_completes() -> None:
    gateway = FakeExecutionGateway(
        [
            successful_execution("5\n"),
            successful_execution("999\n"),
            successful_execution(),
        ]
    )
    workflow, uow, _, submission = build_workflow(gateway=gateway)

    result = workflow.execute(submission_id=1)

    assert result.was_already_completed is False
    assert result.stored_result.result.score.final_score == Decimal("70.00")
    assert submission.status is SubmissionStatus.COMPLETED
    assert uow.commits == 2

    outcomes = result.stored_result.result.outcomes
    assert outcomes[0].status is EvaluationStatus.PASSED
    assert outcomes[0].earned_points == 40
    assert outcomes[1].status is EvaluationStatus.FAILED
    assert outcomes[1].earned_points == 0
    assert outcomes[1].is_hidden is True
    assert outcomes[2].component.value == "unit"
    assert outcomes[3].component.value == "static"


def test_io_comparison_normalizes_crlf_and_outer_whitespace() -> None:
    gateway = FakeExecutionGateway(
        [
            successful_execution("  5\r\n"),
            successful_execution("0\n"),
            successful_execution(),
        ]
    )
    workflow, _, _, _ = build_workflow(gateway=gateway)

    result = workflow.execute(submission_id=1)

    io_outcomes = result.stored_result.result.outcomes[:2]
    assert all(
        item.status is EvaluationStatus.PASSED
        for item in io_outcomes
    )


def test_unit_tests_are_appended_to_student_source() -> None:
    gateway = FakeExecutionGateway(
        [
            successful_execution("5"),
            successful_execution("0"),
            successful_execution(),
        ]
    )
    workflow, _, _, _ = build_workflow(gateway=gateway)

    workflow.execute(submission_id=1)

    unit_request = gateway.requests[2]
    assert "def solve(a, b):" in unit_request.source_code
    assert "# Instructor unit tests" in unit_request.source_code
    assert "assert solve(2, 3) == 5" in unit_request.source_code


def test_static_analyzer_receives_assignment_rules() -> None:
    analyzer = FakeSourceAnalyzer()
    gateway = FakeExecutionGateway(
        [
            successful_execution("5"),
            successful_execution("0"),
            successful_execution(),
        ]
    )
    workflow, _, assignment, submission = build_workflow(
        gateway=gateway,
        analyzer=analyzer,
    )

    workflow.execute(submission_id=1)

    assert len(analyzer.calls) == 1
    analyzed_source, rules = analyzer.calls[0]
    assert analyzed_source == submission.source_code.content
    assert rules == assignment.static_analysis_rules


def test_student_timeout_is_grading_evidence_not_platform_failure() -> None:
    gateway = FakeExecutionGateway(
        [
            ExecutionOutcome(status=EvaluationStatus.TIMEOUT),
            successful_execution("0"),
            successful_execution(),
        ]
    )
    workflow, _, _, submission = build_workflow(gateway=gateway)

    result = workflow.execute(submission_id=1)

    assert submission.status is SubmissionStatus.COMPLETED
    assert result.stored_result.result.outcomes[0].status is (
        EvaluationStatus.TIMEOUT
    )
    assert result.stored_result.result.outcomes[0].earned_points == 0


def test_execution_service_failure_marks_submission_failed_without_result() -> None:
    gateway = FakeExecutionGateway(
        error=CodeExecutionUnavailableError("judge unavailable")
    )
    workflow, uow, _, submission = build_workflow(gateway=gateway)

    with pytest.raises(CodeExecutionUnavailableError):
        workflow.execute(submission_id=1)

    assert submission.status is SubmissionStatus.FAILED
    assert submission.failure_reason == "Execution service failure."
    assert uow.grading_results.get_by_submission_id(1) is None
    assert uow.commits == 2


def test_completed_submission_is_idempotent() -> None:
    gateway = FakeExecutionGateway(
        [
            successful_execution("5"),
            successful_execution("0"),
            successful_execution(),
        ]
    )
    workflow, uow, _, submission = build_workflow(gateway=gateway)

    first = workflow.execute(submission_id=1)
    calls_after_first = len(gateway.requests)
    second = workflow.execute(submission_id=1)

    assert submission.status is SubmissionStatus.COMPLETED
    assert second.was_already_completed is True
    assert second.stored_result.id == first.stored_result.id
    assert len(gateway.requests) == calls_after_first


def test_completed_submission_without_result_is_inconsistent() -> None:
    assignment = make_assignment()
    repository = FakeAssignmentRepository([assignment])
    assert assignment.id is not None
    submission = make_submission(assignment.id)
    submission.start_grading()
    submission.complete_grading()
    uow = FakeGradingUnitOfWork(
        assignments=list(repository._assignments.values()),
        submissions=[submission],
    )

    with pytest.raises(GradingResultMissingError):
        GradeSubmission(
            unit_of_work=uow,
            execution_gateway=FakeExecutionGateway(),
            source_analyzer=FakeSourceAnalyzer(),
        ).execute(submission_id=1)


def test_running_submission_is_not_graded_twice() -> None:
    assignment = make_assignment()
    repository = FakeAssignmentRepository([assignment])
    assert assignment.id is not None
    submission = make_submission(assignment.id)
    submission.start_grading()
    uow = FakeGradingUnitOfWork(
        assignments=list(repository._assignments.values()),
        submissions=[submission],
    )

    with pytest.raises(SubmissionAlreadyRunningError):
        GradeSubmission(
            unit_of_work=uow,
            execution_gateway=FakeExecutionGateway(),
            source_analyzer=FakeSourceAnalyzer(),
        ).execute(submission_id=1)


def test_missing_submission_is_rejected() -> None:
    uow = FakeGradingUnitOfWork()

    with pytest.raises(GradingSubmissionNotFoundError):
        GradeSubmission(
            unit_of_work=uow,
            execution_gateway=FakeExecutionGateway(),
            source_analyzer=FakeSourceAnalyzer(),
        ).execute(submission_id=999)


def test_missing_assignment_is_rejected() -> None:
    submission = Submission(
        id=1,
        assignment_id=999,
        student_id=20,
        attempt_number=1,
        source_code=SourceCode("print('hello')"),
    )
    uow = FakeGradingUnitOfWork(submissions=[submission])

    with pytest.raises(GradingAssignmentNotFoundError):
        GradeSubmission(
            unit_of_work=uow,
            execution_gateway=FakeExecutionGateway(),
            source_analyzer=FakeSourceAnalyzer(),
        ).execute(submission_id=1)


def test_failed_static_analysis_awards_zero_static_points() -> None:
    analyzer = FakeSourceAnalyzer(
        SourceAnalysisReport(
            syntax_valid=True,
            missing_required_functions=("solve",),
            forbidden_imports_found=("os",),
            observed_max_cyclomatic_complexity=12,
            max_cyclomatic_complexity_allowed=10,
        )
    )
    gateway = FakeExecutionGateway(
        [
            successful_execution("5"),
            successful_execution("0"),
            successful_execution(),
        ]
    )
    workflow, _, _, _ = build_workflow(
        gateway=gateway,
        analyzer=analyzer,
    )

    result = workflow.execute(submission_id=1)
    static_outcome = result.stored_result.result.outcomes[-1]

    assert static_outcome.status is EvaluationStatus.FAILED
    assert static_outcome.earned_points == 0
    assert "Missing required functions" in (static_outcome.detail or "")
    assert "Forbidden imports" in (static_outcome.detail or "")
