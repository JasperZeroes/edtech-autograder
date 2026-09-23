from __future__ import annotations

from dataclasses import dataclass

from app.domain.assessment import ExecutionLimits


@dataclass(frozen=True, slots=True)
class CodeExecutionRequest:
    source_code: str
    execution_limits: ExecutionLimits
    stdin: str | None = None

    def __post_init__(self) -> None:
        if not self.source_code.strip():
            raise ValueError("Execution source code must not be blank.")


@dataclass(frozen=True, slots=True)
class SourceAnalysisReport:
    syntax_valid: bool
    missing_required_functions: tuple[str, ...]
    forbidden_imports_found: tuple[str, ...]
    observed_max_cyclomatic_complexity: int | None
    max_cyclomatic_complexity_allowed: int | None
    syntax_error: str | None = None

    @property
    def complexity_within_limit(self) -> bool | None:
        if self.max_cyclomatic_complexity_allowed is None:
            return None
        if self.observed_max_cyclomatic_complexity is None:
            return False
        return (
            self.observed_max_cyclomatic_complexity
            <= self.max_cyclomatic_complexity_allowed
        )

    @property
    def passed(self) -> bool:
        if not self.syntax_valid:
            return False
        if self.missing_required_functions:
            return False
        if self.forbidden_imports_found:
            return False
        if self.complexity_within_limit is False:
            return False
        return True
