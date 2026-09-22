from __future__ import annotations

from typing import Protocol

from .assignment import Assignment


class AssignmentRepository(Protocol):
    """Persistence contract expressed in assessment-domain language."""

    def get_by_id(self, assignment_id: int) -> Assignment | None:
        ...

    def list_by_instructor(self, instructor_id: int) -> list[Assignment]:
        ...

    def list_published(self) -> list[Assignment]:
        ...

    def save(self, assignment: Assignment) -> Assignment:
        ...
