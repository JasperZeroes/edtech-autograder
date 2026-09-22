from __future__ import annotations

from app.domain.submission import SourceCode, Submission

from .commands import CreateSubmissionCommand
from .dto import SubmissionView
from .errors import (
    AssignmentUnavailableError,
    SubmissionAccessError,
    SubmissionNotFoundError,
)
from .ports import SubmissionUnitOfWork


class CreateSubmission:
    def __init__(self, *, unit_of_work: SubmissionUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    def execute(self, command: CreateSubmissionCommand) -> SubmissionView:
        assignment = self._unit_of_work.assignments.get_by_id(
            command.assignment_id
        )

        if assignment is None or not assignment.is_published:
            raise AssignmentUnavailableError(
                f"Assignment {command.assignment_id} is not available "
                "for submission."
            )

        attempt_number = self._unit_of_work.submissions.next_attempt_number(
            assignment_id=command.assignment_id,
            student_id=command.student_id,
        )

        submission = Submission.queue(
            assignment_id=command.assignment_id,
            student_id=command.student_id,
            attempt_number=attempt_number,
            source_code=SourceCode(command.source_code),
        )

        try:
            saved = self._unit_of_work.submissions.save(submission)
            self._unit_of_work.commit()
        except Exception:
            self._unit_of_work.rollback()
            raise

        return SubmissionView.from_domain(saved)


class ListStudentSubmissions:
    def __init__(self, *, unit_of_work: SubmissionUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    def execute(self, *, student_id: int) -> list[SubmissionView]:
        return [
            SubmissionView.from_domain(submission)
            for submission in self._unit_of_work.submissions.list_by_student(
                student_id
            )
        ]


class GetStudentSubmission:
    def __init__(self, *, unit_of_work: SubmissionUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    def execute(
        self,
        *,
        submission_id: int,
        student_id: int,
    ) -> SubmissionView:
        submission = self._unit_of_work.submissions.get_by_id(submission_id)
        if submission is None:
            raise SubmissionNotFoundError(
                f"Submission {submission_id} was not found."
            )

        if submission.student_id != student_id:
            raise SubmissionAccessError(
                "Students may access only their own submissions."
            )

        return SubmissionView.from_domain(submission)
