from __future__ import annotations

from dataclasses import dataclass

from app.domain.assessment import Assignment, GradingTestVisibility
from app.domain.grading import (
    EvaluationOutcome,
    EvaluationStatus,
    GradingComponent,
    GradingResult,
    StoredGradingResult,
)
from app.domain.submission import SubmissionStatus

from .errors import (
    CodeExecutionError,
    GradingAssignmentNotFoundError,
    GradingResultMissingError,
    GradingSubmissionNotFoundError,
    SubmissionAlreadyRunningError,
)
from .ports import CodeExecutionGateway, GradingUnitOfWork, SourceAnalyzer
from .requests import CodeExecutionRequest, SourceAnalysisReport


@dataclass(frozen=True, slots=True)
class GradeSubmissionResult:
    stored_result: StoredGradingResult
    was_already_completed: bool = False


class GradeSubmission:
    """Deterministic orchestration for one persisted submission attempt."""

    def __init__(
        self,
        *,
        unit_of_work: GradingUnitOfWork,
        execution_gateway: CodeExecutionGateway,
        source_analyzer: SourceAnalyzer,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._execution_gateway = execution_gateway
        self._source_analyzer = source_analyzer

    def execute(self, *, submission_id: int) -> GradeSubmissionResult:
        submission = self._unit_of_work.submissions.get_by_id(submission_id)
        if submission is None:
            raise GradingSubmissionNotFoundError(
                f"Submission {submission_id} was not found."
            )

        if submission.status is SubmissionStatus.COMPLETED:
            existing = self._unit_of_work.grading_results.get_by_submission_id(
                submission_id
            )
            if existing is None:
                raise GradingResultMissingError(
                    f"Completed submission {submission_id} has no grading result."
                )
            return GradeSubmissionResult(
                stored_result=existing,
                was_already_completed=True,
            )

        if submission.status is SubmissionStatus.RUNNING:
            raise SubmissionAlreadyRunningError(
                f"Submission {submission_id} is already being graded."
            )

        if submission.status is SubmissionStatus.FAILED:
            raise SubmissionAlreadyRunningError(
                f"Submission {submission_id} is already terminal with status failed."
            )

        assignment = self._unit_of_work.assignments.get_by_id(
            submission.assignment_id
        )
        if assignment is None:
            raise GradingAssignmentNotFoundError(
                f"Assignment {submission.assignment_id} referenced by "
                f"submission {submission_id} was not found."
            )

        submission.start_grading()
        self._unit_of_work.submissions.save(submission)
        self._unit_of_work.commit()

        try:
            outcomes = self._evaluate(
                assignment=assignment,
                source_code=submission.source_code.content,
            )
            result = GradingResult.build(
                policy=assignment.grading_policy,
                outcomes=outcomes,
            )

            stored = self._unit_of_work.grading_results.save(
                submission_id=submission_id,
                result=result,
            )
            submission.complete_grading()
            self._unit_of_work.submissions.save(submission)
            self._unit_of_work.commit()

            return GradeSubmissionResult(stored_result=stored)

        except CodeExecutionError as exc:
            self._fail_submission(
                submission=submission,
                reason="Execution service failure.",
            )
            raise
        except Exception:
            self._unit_of_work.rollback()
            self._fail_submission(
                submission=submission,
                reason="Unexpected grading workflow failure.",
            )
            raise

    def _evaluate(
        self,
        *,
        assignment: Assignment,
        source_code: str,
    ) -> tuple[EvaluationOutcome, ...]:
        outcomes: list[EvaluationOutcome] = []

        if assignment.grading_policy.io_weight > 0:
            outcomes.extend(
                self._evaluate_io(
                    assignment=assignment,
                    source_code=source_code,
                )
            )

        if assignment.grading_policy.unit_weight > 0:
            outcomes.append(
                self._evaluate_unit(
                    assignment=assignment,
                    source_code=source_code,
                )
            )

        if assignment.grading_policy.static_weight > 0:
            outcomes.append(
                self._evaluate_static(
                    assignment=assignment,
                    source_code=source_code,
                )
            )

        return tuple(outcomes)

    def _evaluate_io(
        self,
        *,
        assignment: Assignment,
        source_code: str,
    ) -> tuple[EvaluationOutcome, ...]:
        outcomes: list[EvaluationOutcome] = []

        for test_case in assignment.ordered_io_test_cases:
            execution = self._execution_gateway.execute(
                CodeExecutionRequest(
                    source_code=source_code,
                    stdin=test_case.stdin,
                    execution_limits=assignment.execution_limits,
                )
            )

            detail: str | None = None
            status = execution.status
            earned = 0

            if execution.status is EvaluationStatus.PASSED:
                actual = self._normalize_output(execution.stdout)
                expected = self._normalize_output(
                    test_case.expected_stdout
                )
                if actual == expected:
                    status = EvaluationStatus.PASSED
                    earned = test_case.points
                    detail = "Output matched expected output."
                else:
                    status = EvaluationStatus.FAILED
                    detail = (
                        f"Expected output {expected!r}; "
                        f"received {actual!r}."
                    )
            elif execution.status is EvaluationStatus.TIMEOUT:
                detail = "Execution exceeded the configured time limit."
            elif execution.stderr:
                detail = execution.stderr

            outcomes.append(
                EvaluationOutcome(
                    component=GradingComponent.IO,
                    name=test_case.name,
                    status=status,
                    earned_points=earned,
                    possible_points=test_case.points,
                    is_hidden=(
                        test_case.visibility
                        is GradingTestVisibility.HIDDEN
                    ),
                    detail=detail,
                )
            )

        return tuple(outcomes)

    def _evaluate_unit(
        self,
        *,
        assignment: Assignment,
        source_code: str,
    ) -> EvaluationOutcome:
        specification = assignment.unit_test_spec
        if specification is None:
            raise RuntimeError(
                "Published grading policy requires a unit-test specification."
            )

        combined_source = (
            f"{source_code.rstrip()}\n\n"
            "# Instructor unit tests\n"
            f"{specification.test_code}\n"
        )

        execution = self._execution_gateway.execute(
            CodeExecutionRequest(
                source_code=combined_source,
                execution_limits=assignment.execution_limits,
            )
        )

        earned = (
            specification.points
            if execution.status is EvaluationStatus.PASSED
            else 0
        )

        detail = None
        if execution.status is EvaluationStatus.PASSED:
            detail = "Unit-test specification completed successfully."
        elif execution.status is EvaluationStatus.TIMEOUT:
            detail = "Unit-test execution exceeded the configured time limit."
        elif execution.stderr:
            detail = execution.stderr

        return EvaluationOutcome(
            component=GradingComponent.UNIT,
            name=specification.name,
            status=execution.status,
            earned_points=earned,
            possible_points=specification.points,
            is_hidden=(
                specification.visibility
                is GradingTestVisibility.HIDDEN
            ),
            detail=detail,
        )

    def _evaluate_static(
        self,
        *,
        assignment: Assignment,
        source_code: str,
    ) -> EvaluationOutcome:
        rules = assignment.static_analysis_rules
        if rules is None:
            raise RuntimeError(
                "Published grading policy requires static-analysis rules."
            )

        report = self._source_analyzer.analyze(
            source_code=source_code,
            rules=rules,
        )

        return EvaluationOutcome(
            component=GradingComponent.STATIC,
            name="static analysis",
            status=(
                EvaluationStatus.PASSED
                if report.passed
                else EvaluationStatus.FAILED
            ),
            earned_points=rules.points if report.passed else 0,
            possible_points=rules.points,
            is_hidden=False,
            detail=self._static_detail(report),
        )

    def _fail_submission(self, *, submission, reason: str) -> None:
        try:
            if submission.status is SubmissionStatus.RUNNING:
                submission.fail_grading(reason=reason)
                self._unit_of_work.submissions.save(submission)
                self._unit_of_work.commit()
        except Exception:
            self._unit_of_work.rollback()

    @staticmethod
    def _normalize_output(value: str) -> str:
        return value.replace("\r\n", "\n").strip()

    @staticmethod
    def _static_detail(report: SourceAnalysisReport) -> str:
        parts: list[str] = []

        if not report.syntax_valid:
            parts.append(
                f"Syntax invalid: {report.syntax_error or 'unknown syntax error'}."
            )
        if report.missing_required_functions:
            parts.append(
                "Missing required functions: "
                + ", ".join(report.missing_required_functions)
                + "."
            )
        if report.forbidden_imports_found:
            parts.append(
                "Forbidden imports found: "
                + ", ".join(report.forbidden_imports_found)
                + "."
            )
        if report.complexity_within_limit is False:
            parts.append(
                "Cyclomatic complexity exceeded the configured limit."
            )

        return " ".join(parts) or "Static-analysis requirements satisfied."
