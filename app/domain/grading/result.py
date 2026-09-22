from __future__ import annotations

from dataclasses import dataclass

from app.domain.assessment import GradingPolicy

from .feedback import FeedbackFact, build_feedback_facts
from .outcomes import EvaluationOutcome
from .scoring import ScoreBreakdown


@dataclass(frozen=True, slots=True)
class VisibleEvaluationOutcome:
    component: str
    name: str
    status: str
    earned_points: int
    possible_points: int
    detail: str | None


@dataclass(frozen=True, slots=True)
class HiddenEvaluationSummary:
    total: int
    passed: int
    failed_or_other: int


@dataclass(frozen=True, slots=True)
class StudentGradingView:
    score: ScoreBreakdown
    visible_outcomes: tuple[VisibleEvaluationOutcome, ...]
    hidden_summary: HiddenEvaluationSummary
    feedback_facts: tuple[FeedbackFact, ...]


@dataclass(frozen=True, slots=True)
class GradingResult:
    policy: GradingPolicy
    outcomes: tuple[EvaluationOutcome, ...]
    score: ScoreBreakdown

    @classmethod
    def build(
        cls,
        *,
        policy: GradingPolicy,
        outcomes: tuple[EvaluationOutcome, ...],
    ) -> "GradingResult":
        return cls(
            policy=policy,
            outcomes=outcomes,
            score=ScoreBreakdown.calculate(
                policy=policy,
                outcomes=outcomes,
            ),
        )

    def student_view(self) -> StudentGradingView:
        visible = tuple(
            VisibleEvaluationOutcome(
                component=outcome.component.value,
                name=outcome.name,
                status=outcome.status.value,
                earned_points=outcome.earned_points,
                possible_points=outcome.possible_points,
                detail=outcome.detail,
            )
            for outcome in self.outcomes
            if not outcome.is_hidden
        )

        hidden = tuple(
            outcome for outcome in self.outcomes if outcome.is_hidden
        )
        hidden_passed = sum(1 for outcome in hidden if outcome.passed)

        return StudentGradingView(
            score=self.score,
            visible_outcomes=visible,
            hidden_summary=HiddenEvaluationSummary(
                total=len(hidden),
                passed=hidden_passed,
                failed_or_other=len(hidden) - hidden_passed,
            ),
            feedback_facts=build_feedback_facts(self.outcomes),
        )
