from __future__ import annotations

from typing import Protocol

from .submission import Submission


class SubmissionRepository(Protocol):
    """Persistence contract for submission attempts."""

    def get_by_id(self, submission_id: int) -> Submission | None:
        ...

    def list_by_student(self, student_id: int) -> list[Submission]:
        ...

    def list_by_assignment(self, assignment_id: int) -> list[Submission]:
        ...

    def next_attempt_number(
        self,
        *,
        assignment_id: int,
        student_id: int,
    ) -> int:
        ...

    def save(self, submission: Submission) -> Submission:
        ...
