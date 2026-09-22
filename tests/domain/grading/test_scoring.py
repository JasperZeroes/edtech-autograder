from decimal import Decimal

import pytest

from app.domain.assessment import GradingPolicy
from app.domain.grading import (
    EvaluationOutcome,
    EvaluationStatus,
    GradingCalculationError,
    GradingComponent,
    ScoreBreakdown,
)


def outcome(
    component: GradingComponent,
    *,
    earned: int,
    possible: int,
) -> EvaluationOutcome:
    return EvaluationOutcome(
        component=component,
        name=f"{component.value}-check",
        status=(
            EvaluationStatus.PASSED
            if earned == possible
            else EvaluationStatus.FAILED
        ),
        earned_points=earned,
        possible_points=possible,
    )


def test_component_scores_are_normalized_before_weights_are_applied() -> None:
    policy = GradingPolicy(
        io_weight=70,
        unit_weight=20,
        static_weight=10,
    )
    outcomes = (
        outcome(GradingComponent.IO, earned=50, possible=100),
        outcome(GradingComponent.UNIT, earned=20, possible=20),
        outcome(GradingComponent.STATIC, earned=5, possible=10),
    )

    result = ScoreBreakdown.calculate(
        policy=policy,
        outcomes=outcomes,
    )

    assert result.io.percentage == Decimal("50.00")
    assert result.io.contribution == Decimal("35.00")

    assert result.unit.percentage == Decimal("100.00")
    assert result.unit.contribution == Decimal("20.00")

    assert result.static.percentage == Decimal("50.00")
    assert result.static.contribution == Decimal("5.00")

    assert result.final_score == Decimal("60.00")


def test_raw_points_do_not_bypass_configured_weights() -> None:
    policy = GradingPolicy(
        io_weight=70,
        unit_weight=20,
        static_weight=10,
    )
    outcomes = (
        outcome(GradingComponent.IO, earned=70, possible=70),
        outcome(GradingComponent.UNIT, earned=0, possible=20),
        outcome(GradingComponent.STATIC, earned=0, possible=10),
    )

    result = ScoreBreakdown.calculate(
        policy=policy,
        outcomes=outcomes,
    )

    assert result.io.percentage == Decimal("100.00")
    assert result.io.contribution == Decimal("70.00")
    assert result.final_score == Decimal("70.00")


def test_multiple_outcomes_within_component_are_aggregated() -> None:
    policy = GradingPolicy(
        io_weight=100,
        unit_weight=0,
        static_weight=0,
    )
    outcomes = (
        EvaluationOutcome(
            component=GradingComponent.IO,
            name="case one",
            status=EvaluationStatus.PASSED,
            earned_points=30,
            possible_points=30,
        ),
        EvaluationOutcome(
            component=GradingComponent.IO,
            name="case two",
            status=EvaluationStatus.FAILED,
            earned_points=10,
            possible_points=70,
        ),
    )

    result = ScoreBreakdown.calculate(
        policy=policy,
        outcomes=outcomes,
    )

    assert result.io.percentage == Decimal("40.00")
    assert result.io.contribution == Decimal("40.00")
    assert result.final_score == Decimal("40.00")


def test_zero_weight_component_does_not_require_possible_points() -> None:
    policy = GradingPolicy(
        io_weight=100,
        unit_weight=0,
        static_weight=0,
    )
    outcomes = (
        outcome(GradingComponent.IO, earned=75, possible=100),
    )

    result = ScoreBreakdown.calculate(
        policy=policy,
        outcomes=outcomes,
    )

    assert result.final_score == Decimal("75.00")
    assert result.unit.contribution == Decimal("0.00")
    assert result.static.contribution == Decimal("0.00")


@pytest.mark.parametrize(
    ("policy", "outcomes", "missing_component"),
    [
        (
            GradingPolicy(io_weight=70, unit_weight=20, static_weight=10),
            (
                outcome(
                    GradingComponent.IO,
                    earned=100,
                    possible=100,
                ),
                outcome(
                    GradingComponent.STATIC,
                    earned=10,
                    possible=10,
                ),
            ),
            "unit",
        ),
        (
            GradingPolicy(io_weight=70, unit_weight=20, static_weight=10),
            (
                outcome(
                    GradingComponent.IO,
                    earned=100,
                    possible=100,
                ),
                outcome(
                    GradingComponent.UNIT,
                    earned=20,
                    possible=20,
                ),
            ),
            "static",
        ),
    ],
)
def test_positive_weight_component_requires_evaluated_points(
    policy: GradingPolicy,
    outcomes: tuple[EvaluationOutcome, ...],
    missing_component: str,
) -> None:
    with pytest.raises(
        GradingCalculationError,
        match=missing_component,
    ):
        ScoreBreakdown.calculate(
            policy=policy,
            outcomes=outcomes,
        )


def test_rounding_is_deterministic_to_two_decimal_places() -> None:
    policy = GradingPolicy(
        io_weight=100,
        unit_weight=0,
        static_weight=0,
    )
    outcomes = (
        outcome(GradingComponent.IO, earned=1, possible=3),
    )

    result = ScoreBreakdown.calculate(
        policy=policy,
        outcomes=outcomes,
    )

    assert result.io.percentage == Decimal("33.33")
    assert result.final_score == Decimal("33.33")
