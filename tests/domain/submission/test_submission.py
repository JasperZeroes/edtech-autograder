import pytest

from app.domain.submission import (
    InvalidSubmissionTransitionError,
    SourceCode,
    Submission,
    SubmissionStatus,
    SubmissionValidationError,
)


def make_submission() -> Submission:
    return Submission.queue(
        assignment_id=10,
        student_id=20,
        attempt_number=1,
        source_code=SourceCode("print('hello')"),
    )


def test_queue_creates_first_class_queued_attempt() -> None:
    submission = make_submission()

    assert submission.id is None
    assert submission.assignment_id == 10
    assert submission.student_id == 20
    assert submission.attempt_number == 1
    assert submission.status is SubmissionStatus.QUEUED
    assert submission.failure_reason is None
    assert submission.is_terminal is False


def test_valid_lifecycle_can_complete() -> None:
    submission = make_submission()

    submission.start_grading()
    assert submission.status is SubmissionStatus.RUNNING

    submission.complete_grading()
    assert submission.status is SubmissionStatus.COMPLETED
    assert submission.is_terminal is True


def test_running_submission_can_fail_with_reason() -> None:
    submission = make_submission()
    submission.start_grading()

    submission.fail_grading(reason="  execution timed out  ")

    assert submission.status is SubmissionStatus.FAILED
    assert submission.failure_reason == "execution timed out"
    assert submission.is_terminal is True


@pytest.mark.parametrize(
    "action",
    [
        lambda submission: submission.complete_grading(),
        lambda submission: submission.fail_grading(reason="failed"),
    ],
)
def test_queued_submission_cannot_skip_running_state(action) -> None:
    submission = make_submission()

    with pytest.raises(InvalidSubmissionTransitionError):
        action(submission)


def test_completed_submission_is_terminal() -> None:
    submission = make_submission()
    submission.start_grading()
    submission.complete_grading()

    with pytest.raises(InvalidSubmissionTransitionError):
        submission.start_grading()


def test_failed_submission_is_terminal() -> None:
    submission = make_submission()
    submission.start_grading()
    submission.fail_grading(reason="runtime error")

    with pytest.raises(InvalidSubmissionTransitionError):
        submission.complete_grading()


def test_failure_reason_must_not_be_blank() -> None:
    submission = make_submission()
    submission.start_grading()

    with pytest.raises(SubmissionValidationError):
        submission.fail_grading(reason="   ")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"assignment_id": 0, "student_id": 1, "attempt_number": 1},
        {"assignment_id": 1, "student_id": 0, "attempt_number": 1},
        {"assignment_id": 1, "student_id": 1, "attempt_number": 0},
    ],
)
def test_invalid_submission_identity_is_rejected(
    kwargs: dict[str, int],
) -> None:
    with pytest.raises(SubmissionValidationError):
        Submission.queue(
            **kwargs,
            source_code=SourceCode("print('hello')"),
        )


def test_failed_rehydrated_submission_requires_reason() -> None:
    with pytest.raises(SubmissionValidationError):
        Submission(
            id=1,
            assignment_id=1,
            student_id=1,
            attempt_number=1,
            source_code=SourceCode("print('hello')"),
            status=SubmissionStatus.FAILED,
        )
