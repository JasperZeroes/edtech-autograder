from __future__ import annotations

from dataclasses import dataclass

from app.domain.submission import Submission, SubmissionStatus


@dataclass(frozen=True, slots=True)
class SubmissionView:
    id: int
    assignment_id: int
    student_id: int
    attempt_number: int
    status: SubmissionStatus
    source_code: str
    byte_size: int
    line_count: int
    checksum: str
    failure_reason: str | None

    @classmethod
    def from_domain(cls, submission: Submission) -> "SubmissionView":
        if submission.id is None:
            raise ValueError("A persisted submission id is required.")

        return cls(
            id=submission.id,
            assignment_id=submission.assignment_id,
            student_id=submission.student_id,
            attempt_number=submission.attempt_number,
            status=submission.status,
            source_code=submission.source_code.content,
            byte_size=submission.source_code.byte_size,
            line_count=submission.source_code.line_count,
            checksum=submission.source_code.checksum,
            failure_reason=submission.failure_reason,
        )
