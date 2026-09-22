from __future__ import annotations

from app.domain.assessment import Assignment
from app.domain.submission import Submission
from tests.application.assessment.fakes import FakeAssignmentRepository


class FakeSubmissionRepository:
    def __init__(
        self,
        submissions: list[Submission] | None = None,
    ) -> None:
        self._submissions: dict[int, Submission] = {}
        self._next_id = 1
        self.fail_on_save = False

        for submission in submissions or []:
            self.save(submission)

    def get_by_id(self, submission_id: int) -> Submission | None:
        return self._submissions.get(submission_id)

    def list_by_student(self, student_id: int) -> list[Submission]:
        return [
            submission
            for submission in self._ordered()
            if submission.student_id == student_id
        ]

    def list_by_assignment(self, assignment_id: int) -> list[Submission]:
        return [
            submission
            for submission in self._ordered()
            if submission.assignment_id == assignment_id
        ]

    def next_attempt_number(
        self,
        *,
        assignment_id: int,
        student_id: int,
    ) -> int:
        attempts = [
            submission.attempt_number
            for submission in self._submissions.values()
            if submission.assignment_id == assignment_id
            and submission.student_id == student_id
        ]
        return max(attempts, default=0) + 1

    def save(self, submission: Submission) -> Submission:
        if self.fail_on_save:
            raise RuntimeError("persistence failed")

        if submission.id is None:
            submission.id = self._next_id
            self._next_id += 1
        else:
            self._next_id = max(self._next_id, submission.id + 1)

        self._submissions[submission.id] = submission
        return submission

    def _ordered(self) -> list[Submission]:
        return [
            self._submissions[key]
            for key in sorted(self._submissions)
        ]


class FakeSubmissionUnitOfWork:
    def __init__(
        self,
        *,
        assignments: list[Assignment] | None = None,
        submissions: list[Submission] | None = None,
    ) -> None:
        self.assignments = FakeAssignmentRepository(assignments)
        self.submissions = FakeSubmissionRepository(submissions)
        self.committed = False
        self.rolled_back = False

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True
