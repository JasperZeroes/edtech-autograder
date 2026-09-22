from __future__ import annotations

from app.domain.assessment import Assignment, AssignmentStatus


class FakeAssignmentRepository:
    def __init__(self, assignments: list[Assignment] | None = None) -> None:
        self._assignments: dict[int, Assignment] = {}
        self._next_id = 1
        self.fail_on_save = False

        for assignment in assignments or []:
            self.save(assignment)

    def get_by_id(self, assignment_id: int) -> Assignment | None:
        return self._assignments.get(assignment_id)

    def list_by_instructor(self, instructor_id: int) -> list[Assignment]:
        return [
            assignment
            for assignment in self._ordered()
            if assignment.instructor_id == instructor_id
        ]

    def list_published(self) -> list[Assignment]:
        return [
            assignment
            for assignment in self._ordered()
            if assignment.status is AssignmentStatus.PUBLISHED
        ]

    def save(self, assignment: Assignment) -> Assignment:
        if self.fail_on_save:
            raise RuntimeError("persistence failed")

        if assignment.id is None:
            assignment.id = self._next_id
            self._next_id += 1
        else:
            self._next_id = max(self._next_id, assignment.id + 1)

        self._assignments[assignment.id] = assignment
        return assignment

    def _ordered(self) -> list[Assignment]:
        return [
            self._assignments[key]
            for key in sorted(self._assignments)
        ]


class FakeAssessmentUnitOfWork:
    def __init__(
        self,
        assignments: list[Assignment] | None = None,
    ) -> None:
        self.assignments = FakeAssignmentRepository(assignments)
        self.committed = False
        self.rolled_back = False

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True
