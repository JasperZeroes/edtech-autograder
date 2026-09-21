from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .errors import AssessmentValidationError


_MAX_POINTS = 100_000


class GradingTestVisibility(str, Enum):
    VISIBLE = "visible"
    HIDDEN = "hidden"


def _normalize_name(value: str, *, field_name: str = "name") -> str:
    normalized = value.strip()
    if not 1 <= len(normalized) <= 255:
        raise AssessmentValidationError(
            f"{field_name} must contain between 1 and 255 characters."
        )
    return normalized


def _validate_points(points: int) -> None:
    if not 0 <= points <= _MAX_POINTS:
        raise AssessmentValidationError(
            f"Points must be between 0 and {_MAX_POINTS}."
        )


@dataclass(frozen=True, slots=True)
class IOTestCase:
    name: str
    expected_stdout: str
    stdin: str | None = None
    points: int = 1
    visibility: GradingTestVisibility = GradingTestVisibility.HIDDEN
    order_index: int = 0
    id: int | None = None

    def __post_init__(self) -> None:
        if self.id is not None and self.id <= 0:
            raise AssessmentValidationError(
                "IO test case id must be a positive integer."
            )

        object.__setattr__(self, "name", _normalize_name(self.name))

        if not self.expected_stdout:
            raise AssessmentValidationError(
                "Expected stdout must not be empty."
            )

        _validate_points(self.points)

        if self.order_index < 0:
            raise AssessmentValidationError(
                "IO test order index cannot be negative."
            )


@dataclass(frozen=True, slots=True)
class UnitTestSpecification:
    name: str
    test_code: str
    points: int = 0
    visibility: GradingTestVisibility = GradingTestVisibility.HIDDEN
    id: int | None = None

    def __post_init__(self) -> None:
        if self.id is not None and self.id <= 0:
            raise AssessmentValidationError(
                "Unit-test specification id must be a positive integer."
            )

        object.__setattr__(self, "name", _normalize_name(self.name))

        if not self.test_code.strip():
            raise AssessmentValidationError(
                "Unit-test code must not be empty."
            )

        _validate_points(self.points)


@dataclass(frozen=True, slots=True)
class StaticAnalysisRules:
    required_functions: tuple[str, ...] = ()
    forbidden_imports: tuple[str, ...] = ()
    max_cyclomatic_complexity: int | None = None
    points: int = 0
    id: int | None = None

    def __post_init__(self) -> None:
        if self.id is not None and self.id <= 0:
            raise AssessmentValidationError(
                "Static-analysis rule id must be a positive integer."
            )

        required = self._normalize_items(
            self.required_functions,
            field_name="required function",
        )
        forbidden = self._normalize_items(
            self.forbidden_imports,
            field_name="forbidden import",
        )

        object.__setattr__(self, "required_functions", required)
        object.__setattr__(self, "forbidden_imports", forbidden)

        if (
            self.max_cyclomatic_complexity is not None
            and not 1 <= self.max_cyclomatic_complexity <= 10_000
        ):
            raise AssessmentValidationError(
                "Maximum cyclomatic complexity must be between 1 and 10000."
            )

        _validate_points(self.points)

    @property
    def has_checks(self) -> bool:
        return bool(
            self.required_functions
            or self.forbidden_imports
            or self.max_cyclomatic_complexity is not None
        )

    @staticmethod
    def _normalize_items(
        values: tuple[str, ...],
        *,
        field_name: str,
    ) -> tuple[str, ...]:
        normalized: list[str] = []

        for value in values:
            item = value.strip()
            if not item:
                raise AssessmentValidationError(
                    f"{field_name.capitalize()} must not be blank."
                )
            if item not in normalized:
                normalized.append(item)

        return tuple(normalized)
