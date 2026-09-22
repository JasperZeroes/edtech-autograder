from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.submission import (
    SourceCode,
    Submission,
    SubmissionRepository,
    SubmissionStatus,
)
from app.infrastructure.persistence.models import SubmissionModel


class SubmissionPersistenceError(RuntimeError):
    """Raised when persisted submission state cannot be reconciled."""


class SqlAlchemySubmissionRepository(SubmissionRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, submission_id: int) -> Submission | None:
        model = self._session.get(SubmissionModel, submission_id)
        return self._to_domain(model) if model is not None else None

    def list_by_student(self, student_id: int) -> list[Submission]:
        models = self._session.scalars(
            select(SubmissionModel)
            .where(SubmissionModel.student_id == student_id)
            .order_by(
                SubmissionModel.assignment_id,
                SubmissionModel.attempt_number,
                SubmissionModel.id,
            )
        ).all()
        return [self._to_domain(model) for model in models]

    def list_by_assignment(self, assignment_id: int) -> list[Submission]:
        models = self._session.scalars(
            select(SubmissionModel)
            .where(SubmissionModel.assignment_id == assignment_id)
            .order_by(
                SubmissionModel.student_id,
                SubmissionModel.attempt_number,
                SubmissionModel.id,
            )
        ).all()
        return [self._to_domain(model) for model in models]

    def next_attempt_number(
        self,
        *,
        assignment_id: int,
        student_id: int,
    ) -> int:
        current_max = self._session.scalar(
            select(func.max(SubmissionModel.attempt_number)).where(
                SubmissionModel.assignment_id == assignment_id,
                SubmissionModel.student_id == student_id,
            )
        )
        return (current_max or 0) + 1

    def save(self, submission: Submission) -> Submission:
        if submission.id is None:
            model = SubmissionModel()
            self._session.add(model)
        else:
            model = self._session.get(SubmissionModel, submission.id)
            if model is None:
                raise SubmissionPersistenceError(
                    f"Cannot update submission {submission.id}: "
                    "persistence record does not exist."
                )

        model.assignment_id = submission.assignment_id
        model.student_id = submission.student_id
        model.attempt_number = submission.attempt_number
        model.source_code = submission.source_code.content
        model.status = submission.status.value
        model.failure_reason = submission.failure_reason

        self._session.flush()
        submission.id = model.id
        return submission

    @staticmethod
    def _to_domain(model: SubmissionModel) -> Submission:
        return Submission(
            id=model.id,
            assignment_id=model.assignment_id,
            student_id=model.student_id,
            attempt_number=model.attempt_number,
            source_code=SourceCode(model.source_code),
            status=SubmissionStatus(model.status),
            failure_reason=model.failure_reason,
        )
