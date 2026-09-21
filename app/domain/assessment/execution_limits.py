from __future__ import annotations

from dataclasses import dataclass

from .errors import AssessmentValidationError


@dataclass(frozen=True, slots=True)
class ExecutionLimits:
    """Resource limits applied when submitted code is executed."""

    max_runtime_ms: int = 2_000
    max_memory_kb: int = 128_000

    def __post_init__(self) -> None:
        if not 100 <= self.max_runtime_ms <= 600_000:
            raise AssessmentValidationError(
                "Maximum runtime must be between 100 and 600000 milliseconds."
            )

        if not 16_000 <= self.max_memory_kb <= 2_000_000:
            raise AssessmentValidationError(
                "Maximum memory must be between 16000 and 2000000 KB."
            )
