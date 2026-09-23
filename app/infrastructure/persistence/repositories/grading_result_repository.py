from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain.assessment import GradingPolicy
from app.domain.grading import (
    EvaluationOutcome,
    EvaluationStatus,
    GradingComponent,
    GradingResult,
    GradingResultRepository,
    ScoreBreakdown,
    StoredGradingResult,
    WeightedComponentScore,
    build_feedback_facts,
)
from app.infrastructure.persistence.models import (
    EvaluationOutcomeModel,
    GradingResultModel,
)


class GradingResultPersistenceError(RuntimeError):
    """Raised when grading-result persistence cannot be reconciled."""


class SqlAlchemyGradingResultRepository(GradingResultRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_submission_id(
        self,
        submission_id: int,
    ) -> StoredGradingResult | None:
        model = self._session.scalar(
            select(GradingResultModel)
            .options(selectinload(GradingResultModel.outcomes))
            .where(GradingResultModel.submission_id == submission_id)
        )
        return self._to_domain(model) if model is not None else None

    def save(
        self,
        *,
        submission_id: int,
        result: GradingResult,
    ) -> StoredGradingResult:
        existing = self._session.scalar(
            select(GradingResultModel)
            .options(selectinload(GradingResultModel.outcomes))
            .where(GradingResultModel.submission_id == submission_id)
        )

        if existing is not None:
            raise GradingResultPersistenceError(
                f"Submission {submission_id} already has a grading result."
            )

        model = GradingResultModel(
            submission_id=submission_id,
            io_weight=result.policy.io_weight,
            unit_weight=result.policy.unit_weight,
            static_weight=result.policy.static_weight,
            io_percentage=result.score.io.percentage,
            unit_percentage=result.score.unit.percentage,
            static_percentage=result.score.static.percentage,
            io_contribution=result.score.io.contribution,
            unit_contribution=result.score.unit.contribution,
            static_contribution=result.score.static.contribution,
            final_score=result.score.final_score,
            feedback_facts=[
                {
                    "kind": fact.kind.value,
                    "message": fact.message,
                }
                for fact in build_feedback_facts(result.outcomes)
            ],
            outcomes=[
                EvaluationOutcomeModel(
                    component=outcome.component.value,
                    name=outcome.name,
                    status=outcome.status.value,
                    earned_points=outcome.earned_points,
                    possible_points=outcome.possible_points,
                    is_hidden=outcome.is_hidden,
                    detail=outcome.detail,
                )
                for outcome in result.outcomes
            ],
        )
        self._session.add(model)
        self._session.flush()

        return StoredGradingResult(
            id=model.id,
            submission_id=model.submission_id,
            result=result,
        )

    @staticmethod
    def _weighted(
        *,
        component: GradingComponent,
        weight: int,
        percentage: Decimal,
        contribution: Decimal,
    ) -> WeightedComponentScore:
        return WeightedComponentScore(
            component=component,
            weight=weight,
            percentage=percentage,
            contribution=contribution,
        )

    @classmethod
    def _to_domain(
        cls,
        model: GradingResultModel,
    ) -> StoredGradingResult:
        policy = GradingPolicy(
            io_weight=model.io_weight,
            unit_weight=model.unit_weight,
            static_weight=model.static_weight,
        )

        outcomes = tuple(
            EvaluationOutcome(
                component=GradingComponent(item.component),
                name=item.name,
                status=EvaluationStatus(item.status),
                earned_points=item.earned_points,
                possible_points=item.possible_points,
                is_hidden=item.is_hidden,
                detail=item.detail,
            )
            for item in model.outcomes
        )

        score = ScoreBreakdown(
            io=cls._weighted(
                component=GradingComponent.IO,
                weight=model.io_weight,
                percentage=Decimal(model.io_percentage),
                contribution=Decimal(model.io_contribution),
            ),
            unit=cls._weighted(
                component=GradingComponent.UNIT,
                weight=model.unit_weight,
                percentage=Decimal(model.unit_percentage),
                contribution=Decimal(model.unit_contribution),
            ),
            static=cls._weighted(
                component=GradingComponent.STATIC,
                weight=model.static_weight,
                percentage=Decimal(model.static_percentage),
                contribution=Decimal(model.static_contribution),
            ),
            final_score=Decimal(model.final_score),
        )

        return StoredGradingResult(
            id=model.id,
            submission_id=model.submission_id,
            result=GradingResult(
                policy=policy,
                outcomes=outcomes,
                score=score,
            ),
        )
