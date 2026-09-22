from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .errors import GradingValidationError


class GradingComponent(str, Enum):
    IO = "io"
    UNIT = "unit"
    STATIC = "static"


class EvaluationStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    TIMEOUT = "timeout"


@dataclass(frozen=True, slots=True)
class EvaluationOutcome:
    component: GradingComponent
    name: str
    status: EvaluationStatus
    earned_points: int
    possible_points: int
    is_hidden: bool = True
    detail: str | None = None

    def __post_init__(self) -> None:
        normalized_name = self.name.strip()
        if not normalized_name:
            raise GradingValidationError(
                "Evaluation outcome name must not be blank."
            )
        object.__setattr__(self, "name", normalized_name)

        if self.possible_points < 0:
            raise GradingValidationError(
                "Possible points must not be negative."
            )
        if self.earned_points < 0:
            raise GradingValidationError(
                "Earned points must not be negative."
            )
        if self.earned_points > self.possible_points:
            raise GradingValidationError(
                "Earned points must not exceed possible points."
            )

        if self.detail is not None:
            normalized_detail = self.detail.strip()
            object.__setattr__(self, "detail", normalized_detail or None)

    @property
    def passed(self) -> bool:
        return self.status is EvaluationStatus.PASSED


@dataclass(frozen=True, slots=True)
class ExecutionOutcome:
    status: EvaluationStatus
    stdout: str = ""
    stderr: str = ""
    runtime_ms: int | None = None

    def __post_init__(self) -> None:
        if self.runtime_ms is not None and self.runtime_ms < 0:
            raise GradingValidationError(
                "Execution runtime must not be negative."
            )

    @property
    def succeeded(self) -> bool:
        return self.status is EvaluationStatus.PASSED
