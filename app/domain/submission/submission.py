from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .errors import (
    InvalidSubmissionTransitionError,
    SubmissionValidationError,
)
from .source_code import SourceCode


class SubmissionStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(slots=True)
class Submission:
    """Aggregate root representing one immutable submission attempt."""

    id: int | None
    assignment_id: int
    student_id: int
    attempt_number: int
    source_code: SourceCode
    status: SubmissionStatus = SubmissionStatus.QUEUED
    failure_reason: str | None = None

    def __post_init__(self) -> None:
        if self.id is not None and self.id <= 0:
            raise SubmissionValidationError(
                "Submission id must be a positive integer."
            )

        if self.assignment_id <= 0:
            raise SubmissionValidationError(
                "Assignment id must be a positive integer."
            )

        if self.student_id <= 0:
            raise SubmissionValidationError(
                "Student id must be a positive integer."
            )

        if self.attempt_number <= 0:
            raise SubmissionValidationError(
                "Attempt number must be a positive integer."
            )

        if not isinstance(self.status, SubmissionStatus):
            try:
                self.status = SubmissionStatus(self.status)
            except ValueError as exc:
                raise SubmissionValidationError(
                    "Submission status is invalid."
                ) from exc

        if self.failure_reason is not None:
            reason = self.failure_reason.strip()
            self.failure_reason = reason or None

        if (
            self.status is SubmissionStatus.FAILED
            and self.failure_reason is None
        ):
            raise SubmissionValidationError(
                "A failed submission requires a failure reason."
            )

        if (
            self.status is not SubmissionStatus.FAILED
            and self.failure_reason is not None
        ):
            raise SubmissionValidationError(
                "Only failed submissions may contain a failure reason."
            )

    @classmethod
    def queue(
        cls,
        *,
        assignment_id: int,
        student_id: int,
        attempt_number: int,
        source_code: SourceCode,
    ) -> "Submission":
        return cls(
            id=None,
            assignment_id=assignment_id,
            student_id=student_id,
            attempt_number=attempt_number,
            source_code=source_code,
            status=SubmissionStatus.QUEUED,
        )

    @property
    def is_terminal(self) -> bool:
        return self.status in {
            SubmissionStatus.COMPLETED,
            SubmissionStatus.FAILED,
        }

    def start_grading(self) -> None:
        if self.status is not SubmissionStatus.QUEUED:
            self._raise_transition(SubmissionStatus.RUNNING)

        self.status = SubmissionStatus.RUNNING

    def complete_grading(self) -> None:
        if self.status is not SubmissionStatus.RUNNING:
            self._raise_transition(SubmissionStatus.COMPLETED)

        self.status = SubmissionStatus.COMPLETED
        self.failure_reason = None

    def fail_grading(self, *, reason: str) -> None:
        if self.status is not SubmissionStatus.RUNNING:
            self._raise_transition(SubmissionStatus.FAILED)

        normalized = reason.strip()
        if not normalized:
            raise SubmissionValidationError(
                "A grading failure requires a non-empty reason."
            )

        self.status = SubmissionStatus.FAILED
        self.failure_reason = normalized

    def _raise_transition(self, target: SubmissionStatus) -> None:
        raise InvalidSubmissionTransitionError(
            f"Cannot transition submission from "
            f"{self.status.value} to {target.value}."
        )
