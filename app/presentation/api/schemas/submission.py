from __future__ import annotations

from pydantic import BaseModel

from app.application.submission import SubmissionView
from app.domain.submission import SubmissionStatus


class SubmissionSummaryResponse(BaseModel):
    id: int
    assignment_id: int
    attempt_number: int
    status: SubmissionStatus
    byte_size: int
    line_count: int
    checksum: str
    failure_reason: str | None

    @classmethod
    def from_view(
        cls,
        view: SubmissionView,
    ) -> "SubmissionSummaryResponse":
        return cls(
            id=view.id,
            assignment_id=view.assignment_id,
            attempt_number=view.attempt_number,
            status=view.status,
            byte_size=view.byte_size,
            line_count=view.line_count,
            checksum=view.checksum,
            failure_reason=view.failure_reason,
        )


class SubmissionDetailResponse(SubmissionSummaryResponse):
    student_id: int
    source_code: str

    @classmethod
    def from_view(
        cls,
        view: SubmissionView,
    ) -> "SubmissionDetailResponse":
        return cls(
            id=view.id,
            assignment_id=view.assignment_id,
            student_id=view.student_id,
            attempt_number=view.attempt_number,
            status=view.status,
            source_code=view.source_code,
            byte_size=view.byte_size,
            line_count=view.line_count,
            checksum=view.checksum,
            failure_reason=view.failure_reason,
        )
