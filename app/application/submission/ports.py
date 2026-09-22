from __future__ import annotations

from typing import Protocol

from app.domain.assessment import AssignmentRepository
from app.domain.submission import SubmissionRepository


class GradingQueue(Protocol):
    """Application port for dispatching persisted submissions to grading."""

    def enqueue(self, submission_id: int) -> None:
        ...


class SubmissionUnitOfWork(Protocol):
    assignments: AssignmentRepository
    submissions: SubmissionRepository

    def commit(self) -> None:
        ...

    def rollback(self) -> None:
        ...
