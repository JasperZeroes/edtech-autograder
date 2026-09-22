from __future__ import annotations

from app.domain.assessment import Assignment

from .commands import (
    ConfigureAssignmentCommand,
    CreateAssignmentCommand,
    PublishAssignmentCommand,
    UnpublishAssignmentCommand,
)
from .dto import InstructorAssignmentView, PublishedAssignmentView
from .errors import (
    AssignmentNotFoundError,
    PublishedAssignmentNotFoundError,
)
from .ports import AssessmentUnitOfWork


class CreateAssignment:
    def __init__(self, *, unit_of_work: AssessmentUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    def execute(
        self,
        command: CreateAssignmentCommand,
    ) -> InstructorAssignmentView:
        assignment = Assignment.create(
            instructor_id=command.instructor_id,
            title=command.title,
            description=command.description,
            instructions=command.instructions,
            grading_policy=command.grading_policy,
            execution_limits=command.execution_limits,
        )

        try:
            saved = self._unit_of_work.assignments.save(assignment)
            self._unit_of_work.commit()
        except Exception:
            self._unit_of_work.rollback()
            raise

        return InstructorAssignmentView.from_domain(saved)


class ConfigureAssignment:
    def __init__(self, *, unit_of_work: AssessmentUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    def execute(
        self,
        command: ConfigureAssignmentCommand,
    ) -> InstructorAssignmentView:
        assignment = self._get(command.assignment_id)

        if command.grading_policy is not None:
            assignment.configure_grading_policy(
                instructor_id=command.instructor_id,
                policy=command.grading_policy,
            )

        if command.execution_limits is not None:
            assignment.configure_execution_limits(
                instructor_id=command.instructor_id,
                limits=command.execution_limits,
            )

        for test_case in command.io_test_cases:
            assignment.add_io_test_case(
                instructor_id=command.instructor_id,
                test_case=test_case,
            )

        if command.unit_test_spec is not None:
            assignment.set_unit_test_spec(
                instructor_id=command.instructor_id,
                specification=command.unit_test_spec,
            )

        if command.static_analysis_rules is not None:
            assignment.set_static_analysis_rules(
                instructor_id=command.instructor_id,
                rules=command.static_analysis_rules,
            )

        try:
            saved = self._unit_of_work.assignments.save(assignment)
            self._unit_of_work.commit()
        except Exception:
            self._unit_of_work.rollback()
            raise

        return InstructorAssignmentView.from_domain(saved)

    def _get(self, assignment_id: int) -> Assignment:
        assignment = self._unit_of_work.assignments.get_by_id(assignment_id)
        if assignment is None:
            raise AssignmentNotFoundError(
                f"Assignment {assignment_id} was not found."
            )
        return assignment


class PublishAssignment:
    def __init__(self, *, unit_of_work: AssessmentUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    def execute(
        self,
        command: PublishAssignmentCommand,
    ) -> InstructorAssignmentView:
        assignment = self._unit_of_work.assignments.get_by_id(
            command.assignment_id
        )
        if assignment is None:
            raise AssignmentNotFoundError(
                f"Assignment {command.assignment_id} was not found."
            )

        assignment.publish(instructor_id=command.instructor_id)

        try:
            saved = self._unit_of_work.assignments.save(assignment)
            self._unit_of_work.commit()
        except Exception:
            self._unit_of_work.rollback()
            raise

        return InstructorAssignmentView.from_domain(saved)


class UnpublishAssignment:
    def __init__(self, *, unit_of_work: AssessmentUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    def execute(
        self,
        command: UnpublishAssignmentCommand,
    ) -> InstructorAssignmentView:
        assignment = self._unit_of_work.assignments.get_by_id(
            command.assignment_id
        )
        if assignment is None:
            raise AssignmentNotFoundError(
                f"Assignment {command.assignment_id} was not found."
            )

        assignment.unpublish(instructor_id=command.instructor_id)

        try:
            saved = self._unit_of_work.assignments.save(assignment)
            self._unit_of_work.commit()
        except Exception:
            self._unit_of_work.rollback()
            raise

        return InstructorAssignmentView.from_domain(saved)


class GetInstructorAssignment:
    def __init__(self, *, unit_of_work: AssessmentUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    def execute(
        self,
        *,
        assignment_id: int,
        instructor_id: int,
    ) -> InstructorAssignmentView:
        assignment = self._unit_of_work.assignments.get_by_id(assignment_id)
        if assignment is None:
            raise AssignmentNotFoundError(
                f"Assignment {assignment_id} was not found."
            )

        assignment.assert_owned_by(instructor_id)
        return InstructorAssignmentView.from_domain(assignment)


class ListInstructorAssignments:
    def __init__(self, *, unit_of_work: AssessmentUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    def execute(self, *, instructor_id: int) -> list[InstructorAssignmentView]:
        return [
            InstructorAssignmentView.from_domain(assignment)
            for assignment in self._unit_of_work.assignments.list_by_instructor(
                instructor_id
            )
        ]


class ListPublishedAssignments:
    def __init__(self, *, unit_of_work: AssessmentUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    def execute(self) -> list[PublishedAssignmentView]:
        return [
            PublishedAssignmentView.from_domain(assignment)
            for assignment in self._unit_of_work.assignments.list_published()
        ]


class GetPublishedAssignment:
    def __init__(self, *, unit_of_work: AssessmentUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    def execute(self, *, assignment_id: int) -> PublishedAssignmentView:
        assignment = self._unit_of_work.assignments.get_by_id(assignment_id)

        if assignment is None or not assignment.is_published:
            raise PublishedAssignmentNotFoundError(
                f"Published assignment {assignment_id} was not found."
            )

        return PublishedAssignmentView.from_domain(assignment)
