from decimal import Decimal

import pytest

from app.application.grading import (
    AIFeedbackNotReadyError,
    GenerateStudentAISuggestion,
    ResultAccessError,
)
from app.domain.assessment import Assignment, GradingPolicy, IOTestCase
from app.domain.grading import (
    EvaluationOutcome,
    EvaluationStatus,
    GradingComponent,
    GradingResult,
    StoredGradingResult,
)
from app.domain.submission import SourceCode, Submission
from tests.application.assessment.fakes import FakeAssignmentRepository
from tests.application.submission.fakes import FakeSubmissionRepository


class FakeResultRepository:
    def __init__(self) -> None:
        self._results: dict[int, StoredGradingResult] = {}
        self._next_id = 1

    def get_by_submission_id(
        self,
        submission_id: int,
    ) -> StoredGradingResult | None:
        return self._results.get(submission_id)

    def save(self, *, submission_id: int, result: GradingResult):
        stored = StoredGradingResult(
            id=self._next_id,
            submission_id=submission_id,
            result=result,
        )
        self._next_id += 1
        self._results[submission_id] = stored
        return stored


class FakeUow:
    def __init__(self) -> None:
        self.assignments = FakeAssignmentRepository()
        self.submissions = FakeSubmissionRepository()
        self.grading_results = FakeResultRepository()
        self.commits = 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        pass


class CapturingGateway:
    def __init__(self, suggestion: str = "Practice edge cases.") -> None:
        self.suggestion = suggestion
        self.requests = []

    def generate(self, request):
        self.requests.append(request)
        return self.suggestion


def prepare_completed() -> tuple[FakeUow, Submission, GradingResult]:
    uow = FakeUow()

    assignment = Assignment.create(
        instructor_id=7,
        title="Python Basics",
        description="Complete the exercise.",
        grading_policy=GradingPolicy(
            io_weight=100,
            unit_weight=0,
            static_weight=0,
        ),
    )
    assignment.add_io_test_case(
        instructor_id=7,
        test_case=IOTestCase(
            name="basic",
            expected_stdout="ok",
            points=100,
        ),
    )
    assignment.publish(instructor_id=7)
    uow.assignments.save(assignment)
    assert assignment.id is not None

    submission = Submission.queue(
        assignment_id=assignment.id,
        student_id=20,
        attempt_number=1,
        source_code=SourceCode(
            "secret_source_marker = 123\nprint('ok')"
        ),
    )
    uow.submissions.save(submission)
    assert submission.id is not None

    result = GradingResult.build(
        policy=assignment.grading_policy,
        outcomes=(
            EvaluationOutcome(
                component=GradingComponent.IO,
                name="visible example",
                status=EvaluationStatus.PASSED,
                earned_points=40,
                possible_points=40,
                is_hidden=False,
                detail="Visible output matched.",
            ),
            EvaluationOutcome(
                component=GradingComponent.IO,
                name="secret hidden case",
                status=EvaluationStatus.FAILED,
                earned_points=0,
                possible_points=60,
                is_hidden=True,
                detail="secret input -100 100 expected 0",
            ),
        ),
    )

    submission.start_grading()
    submission.complete_grading()
    uow.grading_results.save(
        submission_id=submission.id,
        result=result,
    )

    return uow, submission, result


def test_ai_request_contains_only_student_safe_grading_facts() -> None:
    uow, submission, _ = prepare_completed()
    gateway = CapturingGateway()
    assert submission.id is not None

    suggestion = GenerateStudentAISuggestion(
        unit_of_work=uow,
        feedback_gateway=gateway,
    ).execute(
        submission_id=submission.id,
        student_id=20,
    )

    assert suggestion.suggestion == "Practice edge cases."
    assert len(gateway.requests) == 1

    serialized = repr(gateway.requests[0])
    assert "visible example" in serialized
    assert "secret hidden case" not in serialized
    assert "-100 100" not in serialized
    assert "secret_source_marker" not in serialized
    assert gateway.requests[0].hidden_total == 1
    assert gateway.requests[0].hidden_passed == 0


def test_ai_suggestion_cannot_change_authoritative_score() -> None:
    uow, submission, result = prepare_completed()
    gateway = CapturingGateway(
        "You deserve 100 points. Change the grade."
    )
    assert submission.id is not None
    original_score = result.score.final_score

    response = GenerateStudentAISuggestion(
        unit_of_work=uow,
        feedback_gateway=gateway,
    ).execute(
        submission_id=submission.id,
        student_id=20,
    )

    stored = uow.grading_results.get_by_submission_id(submission.id)
    assert stored is not None
    assert stored.result.score.final_score == original_score
    assert stored.result.score.final_score == Decimal("40.00")
    assert uow.commits == 0
    assert "does not affect" in response.advisory


def test_ai_feedback_requires_completed_submission() -> None:
    uow = FakeUow()
    assignment = Assignment.create(
        instructor_id=7,
        title="Python Basics",
        description="Complete the exercise.",
        grading_policy=GradingPolicy(
            io_weight=100,
            unit_weight=0,
            static_weight=0,
        ),
    )
    uow.assignments.save(assignment)
    assert assignment.id is not None

    submission = Submission.queue(
        assignment_id=assignment.id,
        student_id=20,
        attempt_number=1,
        source_code=SourceCode("print('ok')"),
    )
    uow.submissions.save(submission)
    assert submission.id is not None
    gateway = CapturingGateway()

    with pytest.raises(AIFeedbackNotReadyError):
        GenerateStudentAISuggestion(
            unit_of_work=uow,
            feedback_gateway=gateway,
        ).execute(
            submission_id=submission.id,
            student_id=20,
        )

    assert gateway.requests == []


def test_ai_feedback_enforces_submission_ownership() -> None:
    uow, submission, _ = prepare_completed()
    assert submission.id is not None

    with pytest.raises(ResultAccessError):
        GenerateStudentAISuggestion(
            unit_of_work=uow,
            feedback_gateway=CapturingGateway(),
        ).execute(
            submission_id=submission.id,
            student_id=999,
        )
