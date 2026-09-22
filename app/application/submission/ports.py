from __future__ import annotations

from typing import Protocol

from app.domain.assessment import AssignmentRepository
from app.domain.submission import SubmissionRepository


class SubmissionUnitOfWork(Protocol):
    assignments: AssignmentRepository
    submissions: SubmissionRepository

    def commit(self) -> None:
        ...

    def rollback(self) -> None:
        ...
