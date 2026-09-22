from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from .errors import SubmissionValidationError


@dataclass(frozen=True, slots=True)
class SourceCode:
    """Immutable Python source submitted for grading."""

    content: str

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise SubmissionValidationError(
                "Submitted source code must not be empty."
            )

    @property
    def byte_size(self) -> int:
        return len(self.content.encode("utf-8"))

    @property
    def line_count(self) -> int:
        return len(self.content.splitlines())

    @property
    def checksum(self) -> str:
        return sha256(self.content.encode("utf-8")).hexdigest()
