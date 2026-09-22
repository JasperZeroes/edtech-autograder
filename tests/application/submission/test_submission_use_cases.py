import pytest

from app.application.submission import (
    AssignmentUnavailableError,
    CreateSubmission,
    CreateSubmissionCommand,
    GetStudentSubmission,
    ListStudentSubmissions,
    SubmissionAccessError,
    SubmissionNotFoundError,
)
from app.domain.assessment import (
    Assignment,
    GradingPolicy,
    IOTestCase,
)
from app.domain.submission import SubmissionStatus, SubmissionValidationError

from .fakes import FakeSubmissionUnitOfWork


def make_assignment(*, published: bool) -> Assignment:
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

    if published:
        assignment.publish(instructor_id=7)

    return assignment


def test_create_submission_requires_published_assignment() -> None:
    draft = make_assignment(published=False)
    unit_of_work = FakeSubmissionUnitOfWork(assignments=[draft])

    with pytest.raises(AssignmentUnavailableError):
        CreateSubmission(unit_of_work=unit_of_work).execute(
            CreateSubmissionCommand(
                assignment_id=draft.id,  # type: ignore[arg-type]
                student_id=20,
                source_code="print('hello')",
            )
        )

    assert unit_of_work.committed is False


def test_create_submission_rejects_missing_assignment() -> None:
    unit_of_work = FakeSubmissionUnitOfWork()

    with pytest.raises(AssignmentUnavailableError):
        CreateSubmission(unit_of_work=unit_of_work).execute(
            CreateSubmissionCommand(
                assignment_id=999,
                student_id=20,
                source_code="print('hello')",
            )
        )


def test_first_submission_is_attempt_one_and_queued() -> None:
    assignment = make_assignment(published=True)
    unit_of_work = FakeSubmissionUnitOfWork(assignments=[assignment])

    result = CreateSubmission(unit_of_work=unit_of_work).execute(
        CreateSubmissionCommand(
            assignment_id=assignment.id,  # type: ignore[arg-type]
            student_id=20,
            source_code="print('hello')",
        )
    )

    assert result.id == 1
    assert result.attempt_number == 1
    assert result.status is SubmissionStatus.QUEUED
    assert result.source_code == "print('hello')"
    assert result.checksum
    assert unit_of_work.committed is True


def test_repeated_submissions_create_historical_attempts() -> None:
    assignment = make_assignment(published=True)
    unit_of_work = FakeSubmissionUnitOfWork(assignments=[assignment])
    use_case = CreateSubmission(unit_of_work=unit_of_work)

    first = use_case.execute(
        CreateSubmissionCommand(
            assignment_id=assignment.id,  # type: ignore[arg-type]
            student_id=20,
            source_code="print('first')",
        )
    )
    second = use_case.execute(
        CreateSubmissionCommand(
            assignment_id=assignment.id,  # type: ignore[arg-type]
            student_id=20,
            source_code="print('second')",
        )
    )

    assert first.attempt_number == 1
    assert second.attempt_number == 2
    assert first.id != second.id
    assert len(unit_of_work.submissions.list_by_student(20)) == 2


def test_attempt_numbers_are_scoped_by_student_and_assignment() -> None:
    first_assignment = make_assignment(published=True)
    second_assignment = make_assignment(published=True)
    unit_of_work = FakeSubmissionUnitOfWork(
        assignments=[first_assignment, second_assignment]
    )
    use_case = CreateSubmission(unit_of_work=unit_of_work)

    first = use_case.execute(
        CreateSubmissionCommand(
            assignment_id=first_assignment.id,  # type: ignore[arg-type]
            student_id=20,
            source_code="print('a')",
        )
    )
    second_student = use_case.execute(
        CreateSubmissionCommand(
            assignment_id=first_assignment.id,  # type: ignore[arg-type]
            student_id=21,
            source_code="print('b')",
        )
    )
    second_assignment_attempt = use_case.execute(
        CreateSubmissionCommand(
            assignment_id=second_assignment.id,  # type: ignore[arg-type]
            student_id=20,
            source_code="print('c')",
        )
    )

    assert first.attempt_number == 1
    assert second_student.attempt_number == 1
    assert second_assignment_attempt.attempt_number == 1


def test_blank_source_code_is_rejected_before_persistence() -> None:
    assignment = make_assignment(published=True)
    unit_of_work = FakeSubmissionUnitOfWork(assignments=[assignment])

    with pytest.raises(SubmissionValidationError):
        CreateSubmission(unit_of_work=unit_of_work).execute(
            CreateSubmissionCommand(
                assignment_id=assignment.id,  # type: ignore[arg-type]
                student_id=20,
                source_code="   ",
            )
        )

    assert unit_of_work.committed is False


def test_create_submission_rolls_back_on_persistence_failure() -> None:
    assignment = make_assignment(published=True)
    unit_of_work = FakeSubmissionUnitOfWork(assignments=[assignment])
    unit_of_work.submissions.fail_on_save = True

    with pytest.raises(RuntimeError, match="persistence failed"):
        CreateSubmission(unit_of_work=unit_of_work).execute(
            CreateSubmissionCommand(
                assignment_id=assignment.id,  # type: ignore[arg-type]
                student_id=20,
                source_code="print('hello')",
            )
        )

    assert unit_of_work.committed is False
    assert unit_of_work.rolled_back is True


def test_list_student_submissions_returns_only_own_history() -> None:
    assignment = make_assignment(published=True)
    unit_of_work = FakeSubmissionUnitOfWork(assignments=[assignment])
    create = CreateSubmission(unit_of_work=unit_of_work)

    create.execute(
        CreateSubmissionCommand(
            assignment_id=assignment.id,  # type: ignore[arg-type]
            student_id=20,
            source_code="print('one')",
        )
    )
    create.execute(
        CreateSubmissionCommand(
            assignment_id=assignment.id,  # type: ignore[arg-type]
            student_id=21,
            source_code="print('other')",
        )
    )
    create.execute(
        CreateSubmissionCommand(
            assignment_id=assignment.id,  # type: ignore[arg-type]
            student_id=20,
            source_code="print('two')",
        )
    )

    results = ListStudentSubmissions(
        unit_of_work=unit_of_work
    ).execute(student_id=20)

    assert [result.attempt_number for result in results] == [1, 2]
    assert all(result.student_id == 20 for result in results)


def test_get_student_submission_enforces_ownership() -> None:
    assignment = make_assignment(published=True)
    unit_of_work = FakeSubmissionUnitOfWork(assignments=[assignment])
    created = CreateSubmission(unit_of_work=unit_of_work).execute(
        CreateSubmissionCommand(
            assignment_id=assignment.id,  # type: ignore[arg-type]
            student_id=20,
            source_code="print('hello')",
        )
    )

    use_case = GetStudentSubmission(unit_of_work=unit_of_work)

    own = use_case.execute(
        submission_id=created.id,
        student_id=20,
    )
    assert own.id == created.id

    with pytest.raises(SubmissionAccessError):
        use_case.execute(
            submission_id=created.id,
            student_id=21,
        )


def test_get_missing_submission_raises_application_error() -> None:
    unit_of_work = FakeSubmissionUnitOfWork()

    with pytest.raises(SubmissionNotFoundError):
        GetStudentSubmission(unit_of_work=unit_of_work).execute(
            submission_id=999,
            student_id=20,
        )
