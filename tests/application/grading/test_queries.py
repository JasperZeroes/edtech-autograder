from decimal import Decimal

import pytest

from app.application.grading import (
    GetInstructorSubmissionResult,
    GetStudentSubmissionResult,
    GradingResultMissingError,
    ListInstructorAssignmentSubmissions,
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


class FakeGradingUow:
    def __init__(self) -> None:
        self.assignments = FakeAssignmentRepository()
        self.submissions = FakeSubmissionRepository()
        self.grading_results = FakeResultRepository()

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass


def make_assignment(uow: FakeGradingUow, *, instructor_id: int = 7) -> Assignment:
    assignment = Assignment.create(
        instructor_id=instructor_id,
        title="Python Basics",
        description="Complete the exercise.",
        grading_policy=GradingPolicy(
            io_weight=100,
            unit_weight=0,
            static_weight=0,
        ),
    )
    assignment.add_io_test_case(
        instructor_id=instructor_id,
        test_case=IOTestCase(
            name="basic",
            expected_stdout="ok",
            points=100,
        ),
    )
    assignment.publish(instructor_id=instructor_id)
    uow.assignments.save(assignment)
    return assignment


def make_submission(
    uow: FakeGradingUow,
    *,
    assignment_id: int,
    student_id: int = 20,
) -> Submission:
    submission = Submission.queue(
        assignment_id=assignment_id,
        student_id=student_id,
        attempt_number=1,
        source_code=SourceCode("print('ok')"),
    )
    uow.submissions.save(submission)
    return submission


def complete_submission(
    uow: FakeGradingUow,
    submission: Submission,
) -> GradingResult:
    result = GradingResult.build(
        policy=GradingPolicy(
            io_weight=100,
            unit_weight=0,
            static_weight=0,
        ),
        outcomes=(
            EvaluationOutcome(
                component=GradingComponent.IO,
                name="visible example",
                status=EvaluationStatus.PASSED,
                earned_points=40,
                possible_points=40,
                is_hidden=False,
                detail="Visible detail.",
            ),
            EvaluationOutcome(
                component=GradingComponent.IO,
                name="secret edge case",
                status=EvaluationStatus.FAILED,
                earned_points=0,
                possible_points=60,
                is_hidden=True,
                detail="Secret input was -100 100.",
            ),
        ),
    )
    submission.start_grading()
    submission.complete_grading()
    assert submission.id is not None
    uow.grading_results.save(
        submission_id=submission.id,
        result=result,
    )
    return result


def test_student_can_poll_queued_submission_without_result() -> None:
    uow = FakeGradingUow()
    assignment = make_assignment(uow)
    assert assignment.id is not None
    submission = make_submission(uow, assignment_id=assignment.id)
    assert submission.id is not None

    view = GetStudentSubmissionResult(
        unit_of_work=uow
    ).execute(
        submission_id=submission.id,
        student_id=20,
    )

    assert view.status.value == "queued"
    assert view.result is None


def test_student_result_hides_hidden_test_identity_and_detail() -> None:
    uow = FakeGradingUow()
    assignment = make_assignment(uow)
    assert assignment.id is not None
    submission = make_submission(uow, assignment_id=assignment.id)
    result = complete_submission(uow, submission)
    assert submission.id is not None

    view = GetStudentSubmissionResult(
        unit_of_work=uow
    ).execute(
        submission_id=submission.id,
        student_id=20,
    )

    assert view.result is not None
    assert view.result.score.final_score == Decimal("40.00")
    assert [item.name for item in view.result.visible_outcomes] == [
        "visible example"
    ]
    assert view.result.hidden_summary.total == 1
    serialized = repr(view)
    assert "secret edge case" not in serialized
    assert "-100 100" not in serialized
    assert result.outcomes[1].name == "secret edge case"


def test_student_cannot_read_another_students_result() -> None:
    uow = FakeGradingUow()
    assignment = make_assignment(uow)
    assert assignment.id is not None
    submission = make_submission(uow, assignment_id=assignment.id)
    assert submission.id is not None

    with pytest.raises(ResultAccessError):
        GetStudentSubmissionResult(
            unit_of_work=uow
        ).execute(
            submission_id=submission.id,
            student_id=999,
        )


def test_completed_submission_without_result_is_detected() -> None:
    uow = FakeGradingUow()
    assignment = make_assignment(uow)
    assert assignment.id is not None
    submission = make_submission(uow, assignment_id=assignment.id)
    submission.start_grading()
    submission.complete_grading()
    assert submission.id is not None

    with pytest.raises(GradingResultMissingError):
        GetStudentSubmissionResult(
            unit_of_work=uow
        ).execute(
            submission_id=submission.id,
            student_id=20,
        )


def test_instructor_listing_contains_status_and_final_score() -> None:
    uow = FakeGradingUow()
    assignment = make_assignment(uow)
    assert assignment.id is not None
    submission = make_submission(uow, assignment_id=assignment.id)
    complete_submission(uow, submission)

    views = ListInstructorAssignmentSubmissions(
        unit_of_work=uow
    ).execute(
        assignment_id=assignment.id,
        instructor_id=7,
    )

    assert len(views) == 1
    assert views[0].student_id == 20
    assert views[0].final_score == Decimal("40.00")


def test_instructor_detail_contains_hidden_evidence() -> None:
    uow = FakeGradingUow()
    assignment = make_assignment(uow)
    assert assignment.id is not None
    submission = make_submission(uow, assignment_id=assignment.id)
    complete_submission(uow, submission)
    assert submission.id is not None

    view = GetInstructorSubmissionResult(
        unit_of_work=uow
    ).execute(
        assignment_id=assignment.id,
        submission_id=submission.id,
        instructor_id=7,
    )

    assert view.result is not None
    hidden = [item for item in view.result.outcomes if item.is_hidden]
    assert len(hidden) == 1
    assert hidden[0].name == "secret edge case"
    assert hidden[0].detail == "Secret input was -100 100."
