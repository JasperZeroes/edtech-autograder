from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CreateSubmissionCommand:
    assignment_id: int
    student_id: int
    source_code: str
