from __future__ import annotations

from typing import Protocol

from app.domain.assessment import AssignmentRepository


class AssessmentUnitOfWork(Protocol):
    """Transaction boundary for assessment application use cases."""

    assignments: AssignmentRepository

    def commit(self) -> None:
        ...

    def rollback(self) -> None:
        ...
