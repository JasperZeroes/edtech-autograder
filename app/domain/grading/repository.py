from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .result import GradingResult


@dataclass(frozen=True, slots=True)
class StoredGradingResult:
    id: int
    submission_id: int
    result: GradingResult


class GradingResultRepository(Protocol):
    """Persistence contract for one authoritative result per submission."""

    def get_by_submission_id(
        self,
        submission_id: int,
    ) -> StoredGradingResult | None:
        ...

    def save(
        self,
        *,
        submission_id: int,
        result: GradingResult,
    ) -> StoredGradingResult:
        ...
