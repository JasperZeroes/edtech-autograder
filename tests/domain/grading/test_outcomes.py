import pytest

from app.domain.grading import (
    EvaluationOutcome,
    EvaluationStatus,
    ExecutionOutcome,
    GradingComponent,
    GradingValidationError,
)


def test_evaluation_outcome_normalizes_name_and_detail() -> None:
    outcome = EvaluationOutcome(
        component=GradingComponent.IO,
        name="  basic case  ",
        status=EvaluationStatus.PASSED,
        earned_points=10,
        possible_points=10,
        is_hidden=False,
        detail="  output matched  ",
    )

    assert outcome.name == "basic case"
    assert outcome.detail == "output matched"
    assert outcome.passed is True


@pytest.mark.parametrize(
    ("earned", "possible"),
    [
        (-1, 10),
        (11, 10),
        (1, -1),
    ],
)
def test_invalid_outcome_points_are_rejected(
    earned: int,
    possible: int,
) -> None:
    with pytest.raises(GradingValidationError):
        EvaluationOutcome(
            component=GradingComponent.IO,
            name="case",
            status=EvaluationStatus.FAILED,
            earned_points=earned,
            possible_points=possible,
        )


def test_blank_outcome_name_is_rejected() -> None:
    with pytest.raises(GradingValidationError):
        EvaluationOutcome(
            component=GradingComponent.UNIT,
            name="   ",
            status=EvaluationStatus.ERROR,
            earned_points=0,
            possible_points=10,
        )


def test_execution_outcome_reports_success() -> None:
    result = ExecutionOutcome(
        status=EvaluationStatus.PASSED,
        stdout="ok\n",
        runtime_ms=24,
    )

    assert result.succeeded is True
    assert result.runtime_ms == 24


def test_negative_execution_runtime_is_rejected() -> None:
    with pytest.raises(GradingValidationError):
        ExecutionOutcome(
            status=EvaluationStatus.ERROR,
            runtime_ms=-1,
        )
