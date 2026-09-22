import pytest

from app.application.submission import (
    AssignmentUnavailableError,
    CreateSubmissionCommand,
    SubmissionQueueError,
    SubmitForGrading,
)
from app.domain.assessment import Assignment, GradingPolicy, IOTestCase

from .fakes import FakeGradingQueue, FakeSubmissionUnitOfWork


def make_published_assignment() -> Assignment:
    assignment = Assignment.create(
        instructor_id=7,
        title="Python Basics",
        description="Solve the exercise.",
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
    return assignment


def test_submission_is_committed_before_enqueue() -> None:
    events: list[str] = []
    assignment = make_published_assignment()
    unit_of_work = FakeSubmissionUnitOfWork(
        assignments=[assignment],
        events=events,
    )
    queue = FakeGradingQueue(events=events)

    result = SubmitForGrading(
        unit_of_work=unit_of_work,
        grading_queue=queue,
    ).execute(
        CreateSubmissionCommand(
            assignment_id=assignment.id,  # type: ignore[arg-type]
            student_id=20,
            source_code="print('hello')",
        )
    )

    assert result.id == 1
    assert events == ["commit", "enqueue:1"]
    assert queue.enqueued == [1]


def test_queue_failure_does_not_rollback_persisted_submission() -> None:
    events: list[str] = []
    assignment = make_published_assignment()
    unit_of_work = FakeSubmissionUnitOfWork(
        assignments=[assignment],
        events=events,
    )
    queue = FakeGradingQueue(
        events=events,
        fail_on_enqueue=True,
    )

    with pytest.raises(SubmissionQueueError) as exc_info:
        SubmitForGrading(
            unit_of_work=unit_of_work,
            grading_queue=queue,
        ).execute(
            CreateSubmissionCommand(
                assignment_id=assignment.id,  # type: ignore[arg-type]
                student_id=20,
                source_code="print('hello')",
            )
        )

    assert exc_info.value.submission_id == 1
    assert unit_of_work.committed is True
    assert unit_of_work.rolled_back is False
    assert unit_of_work.submissions.get_by_id(1) is not None
    assert events == ["commit", "enqueue:1"]


def test_unavailable_assignment_is_never_enqueued() -> None:
    queue = FakeGradingQueue()
    unit_of_work = FakeSubmissionUnitOfWork()

    with pytest.raises(AssignmentUnavailableError):
        SubmitForGrading(
            unit_of_work=unit_of_work,
            grading_queue=queue,
        ).execute(
            CreateSubmissionCommand(
                assignment_id=999,
                student_id=20,
                source_code="print('hello')",
            )
        )

    assert queue.enqueued == []
    assert unit_of_work.committed is False
