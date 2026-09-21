import pytest

from app.domain.assessment import AssessmentValidationError, ExecutionLimits


def test_default_execution_limits_match_phase_one_defaults() -> None:
    limits = ExecutionLimits()

    assert limits.max_runtime_ms == 2_000
    assert limits.max_memory_kb == 128_000


@pytest.mark.parametrize("runtime", [99, 600_001])
def test_runtime_outside_supported_bounds_is_rejected(runtime: int) -> None:
    with pytest.raises(AssessmentValidationError):
        ExecutionLimits(max_runtime_ms=runtime)


@pytest.mark.parametrize("memory", [15_999, 2_000_001])
def test_memory_outside_supported_bounds_is_rejected(memory: int) -> None:
    with pytest.raises(AssessmentValidationError):
        ExecutionLimits(max_memory_kb=memory)
