from __future__ import annotations

from app.domain.submission import SubmissionStatus

from .errors import (
    GradingAssignmentNotFoundError,
    GradingResultMissingError,
    GradingSubmissionNotFoundError,
    ResultAccessError,
)
from .ports import GradingUnitOfWork
from .result_views import (
    InstructorResultPayload,
    InstructorSubmissionResultView,
    InstructorSubmissionSummaryView,
    StudentResultPayload,
    StudentSubmissionResultView,
)


class GetStudentSubmissionResult:
    def __init__(self, *, unit_of_work: GradingUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    def execute(
        self,
        *,
        submission_id: int,
        student_id: int,
    ) -> StudentSubmissionResultView:
        submission = self._unit_of_work.submissions.get_by_id(submission_id)
        if submission is None:
            raise GradingSubmissionNotFoundError(
                f"Submission {submission_id} was not found."
            )

        if submission.student_id != student_id:
            raise ResultAccessError(
                "Students may access only their own grading results."
            )

        stored = self._unit_of_work.grading_results.get_by_submission_id(
            submission_id
        )

        if submission.status is SubmissionStatus.COMPLETED and stored is None:
            raise GradingResultMissingError(
                f"Completed submission {submission_id} has no grading result."
            )

        payload = (
            StudentResultPayload.from_student_view(
                stored.result.student_view()
            )
            if stored is not None
            else None
        )

        return StudentSubmissionResultView(
            submission_id=submission_id,
            assignment_id=submission.assignment_id,
            attempt_number=submission.attempt_number,
            status=submission.status,
            failure_reason=submission.failure_reason,
            result=payload,
        )


class ListInstructorAssignmentSubmissions:
    def __init__(self, *, unit_of_work: GradingUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    def execute(
        self,
        *,
        assignment_id: int,
        instructor_id: int,
    ) -> list[InstructorSubmissionSummaryView]:
        assignment = self._unit_of_work.assignments.get_by_id(assignment_id)
        if assignment is None:
            raise GradingAssignmentNotFoundError(
                f"Assignment {assignment_id} was not found."
            )

        assignment.assert_owned_by(instructor_id)

        views: list[InstructorSubmissionSummaryView] = []
        for submission in self._unit_of_work.submissions.list_by_assignment(
            assignment_id
        ):
            if submission.id is None:
                raise ValueError("A persisted submission id is required.")

            stored = self._unit_of_work.grading_results.get_by_submission_id(
                submission.id
            )

            if (
                submission.status is SubmissionStatus.COMPLETED
                and stored is None
            ):
                raise GradingResultMissingError(
                    f"Completed submission {submission.id} "
                    "has no grading result."
                )

            views.append(
                InstructorSubmissionSummaryView(
                    submission_id=submission.id,
                    assignment_id=submission.assignment_id,
                    student_id=submission.student_id,
                    attempt_number=submission.attempt_number,
                    status=submission.status,
                    failure_reason=submission.failure_reason,
                    final_score=(
                        stored.result.score.final_score
                        if stored is not None
                        else None
                    ),
                )
            )

        return views


class GetInstructorSubmissionResult:
    def __init__(self, *, unit_of_work: GradingUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    def execute(
        self,
        *,
        assignment_id: int,
        submission_id: int,
        instructor_id: int,
    ) -> InstructorSubmissionResultView:
        assignment = self._unit_of_work.assignments.get_by_id(assignment_id)
        if assignment is None:
            raise GradingAssignmentNotFoundError(
                f"Assignment {assignment_id} was not found."
            )

        assignment.assert_owned_by(instructor_id)

        submission = self._unit_of_work.submissions.get_by_id(submission_id)
        if (
            submission is None
            or submission.assignment_id != assignment_id
        ):
            raise GradingSubmissionNotFoundError(
                f"Submission {submission_id} was not found "
                f"for assignment {assignment_id}."
            )

        stored = self._unit_of_work.grading_results.get_by_submission_id(
            submission_id
        )

        if submission.status is SubmissionStatus.COMPLETED and stored is None:
            raise GradingResultMissingError(
                f"Completed submission {submission_id} has no grading result."
            )

        return InstructorSubmissionResultView(
            submission_id=submission_id,
            assignment_id=assignment_id,
            student_id=submission.student_id,
            attempt_number=submission.attempt_number,
            status=submission.status,
            failure_reason=submission.failure_reason,
            result=(
                InstructorResultPayload.from_result(stored.result)
                if stored is not None
                else None
            ),
        )
