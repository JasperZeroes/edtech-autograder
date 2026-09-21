from __future__ import annotations

from dataclasses import dataclass

from .errors import AssessmentValidationError


@dataclass(frozen=True, slots=True)
class GradingPolicy:
    """Percentage contribution of each deterministic grading strategy."""

    io_weight: int = 70
    unit_weight: int = 20
    static_weight: int = 10

    def __post_init__(self) -> None:
        weights = {
            "io_weight": self.io_weight,
            "unit_weight": self.unit_weight,
            "static_weight": self.static_weight,
        }

        for name, value in weights.items():
            if not 0 <= value <= 100:
                raise AssessmentValidationError(
                    f"{name} must be between 0 and 100."
                )

        if sum(weights.values()) != 100:
            raise AssessmentValidationError(
                "Grading weights must total 100 percent."
            )
