from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from app.domain.assessment import GradingPolicy

from .errors import GradingCalculationError, GradingValidationError
from .outcomes import EvaluationOutcome, GradingComponent

_TWO_PLACES = Decimal("0.01")
_HUNDRED = Decimal("100")


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)


@dataclass(frozen=True, slots=True)
class ComponentScore:
    component: GradingComponent
    earned_points: int
    possible_points: int
    percentage: Decimal

    def __post_init__(self) -> None:
        if self.earned_points < 0 or self.possible_points < 0:
            raise GradingValidationError(
                "Component points must not be negative."
            )
        if self.earned_points > self.possible_points:
            raise GradingValidationError(
                "Component earned points must not exceed possible points."
            )
        if self.percentage < Decimal("0") or self.percentage > _HUNDRED:
            raise GradingValidationError(
                "Component percentage must be between 0 and 100."
            )

    @classmethod
    def from_outcomes(
        cls,
        *,
        component: GradingComponent,
        outcomes: tuple[EvaluationOutcome, ...],
    ) -> "ComponentScore":
        component_outcomes = tuple(
            outcome
            for outcome in outcomes
            if outcome.component is component
        )
        earned = sum(outcome.earned_points for outcome in component_outcomes)
        possible = sum(
            outcome.possible_points for outcome in component_outcomes
        )

        percentage = (
            Decimal("0")
            if possible == 0
            else _quantize(
                Decimal(earned) / Decimal(possible) * _HUNDRED
            )
        )

        return cls(
            component=component,
            earned_points=earned,
            possible_points=possible,
            percentage=percentage,
        )


@dataclass(frozen=True, slots=True)
class WeightedComponentScore:
    component: GradingComponent
    weight: int
    percentage: Decimal
    contribution: Decimal

    def __post_init__(self) -> None:
        if self.weight < 0 or self.weight > 100:
            raise GradingValidationError(
                "Component weight must be between 0 and 100."
            )


@dataclass(frozen=True, slots=True)
class ScoreBreakdown:
    io: WeightedComponentScore
    unit: WeightedComponentScore
    static: WeightedComponentScore
    final_score: Decimal

    def __post_init__(self) -> None:
        if self.final_score < Decimal("0") or self.final_score > _HUNDRED:
            raise GradingValidationError(
                "Final score must be between 0 and 100."
            )

    @classmethod
    def calculate(
        cls,
        *,
        policy: GradingPolicy,
        outcomes: tuple[EvaluationOutcome, ...],
    ) -> "ScoreBreakdown":
        component_scores = {
            component: ComponentScore.from_outcomes(
                component=component,
                outcomes=outcomes,
            )
            for component in GradingComponent
        }

        weights = {
            GradingComponent.IO: policy.io_weight,
            GradingComponent.UNIT: policy.unit_weight,
            GradingComponent.STATIC: policy.static_weight,
        }

        weighted: dict[GradingComponent, WeightedComponentScore] = {}

        for component, component_score in component_scores.items():
            weight = weights[component]

            if weight > 0 and component_score.possible_points == 0:
                raise GradingCalculationError(
                    f"{component.value} grading has weight {weight} "
                    "but no possible points were evaluated."
                )

            contribution = _quantize(
                component_score.percentage
                * Decimal(weight)
                / _HUNDRED
            )

            weighted[component] = WeightedComponentScore(
                component=component,
                weight=weight,
                percentage=component_score.percentage,
                contribution=contribution,
            )

        final_score = _quantize(
            sum(
                (score.contribution for score in weighted.values()),
                Decimal("0"),
            )
        )

        return cls(
            io=weighted[GradingComponent.IO],
            unit=weighted[GradingComponent.UNIT],
            static=weighted[GradingComponent.STATIC],
            final_score=final_score,
        )
