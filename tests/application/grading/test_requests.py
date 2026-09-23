import pytest

from app.application.grading import (
    CodeExecutionRequest,
    SourceAnalysisReport,
)
from app.domain.assessment import ExecutionLimits


def test_execution_request_accepts_python_source() -> None:
    request = CodeExecutionRequest(
        source_code="print('hello')",
        stdin="input",
        execution_limits=ExecutionLimits(
            max_runtime_ms=2_000,
            max_memory_kb=128_000,
        ),
    )

    assert request.source_code == "print('hello')"
    assert request.stdin == "input"


def test_execution_request_rejects_blank_source() -> None:
    with pytest.raises(ValueError, match="must not be blank"):
        CodeExecutionRequest(
            source_code="   ",
            execution_limits=ExecutionLimits(),
        )


def test_source_analysis_report_combines_static_checks() -> None:
    passing = SourceAnalysisReport(
        syntax_valid=True,
        missing_required_functions=(),
        forbidden_imports_found=(),
        observed_max_cyclomatic_complexity=4,
        max_cyclomatic_complexity_allowed=5,
    )
    failing = SourceAnalysisReport(
        syntax_valid=True,
        missing_required_functions=("solve",),
        forbidden_imports_found=("os",),
        observed_max_cyclomatic_complexity=8,
        max_cyclomatic_complexity_allowed=5,
    )

    assert passing.complexity_within_limit is True
    assert passing.passed is True

    assert failing.complexity_within_limit is False
    assert failing.passed is False
