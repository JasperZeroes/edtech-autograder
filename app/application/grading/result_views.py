from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.domain.grading import GradingResult, StudentGradingView, build_feedback_facts
from app.domain.submission import SubmissionStatus


@dataclass(frozen=True, slots=True)
class WeightedComponentView:
    weight: int
    percentage: Decimal
    contribution: Decimal


@dataclass(frozen=True, slots=True)
class ScoreBreakdownView:
    io: WeightedComponentView
    unit: WeightedComponentView
    static: WeightedComponentView
    final_score: Decimal

    @classmethod
    def from_result(cls, result: GradingResult) -> "ScoreBreakdownView":
        score = result.score
        return cls(
            io=WeightedComponentView(
                weight=score.io.weight,
                percentage=score.io.percentage,
                contribution=score.io.contribution,
            ),
            unit=WeightedComponentView(
                weight=score.unit.weight,
                percentage=score.unit.percentage,
                contribution=score.unit.contribution,
            ),
            static=WeightedComponentView(
                weight=score.static.weight,
                percentage=score.static.percentage,
                contribution=score.static.contribution,
            ),
            final_score=score.final_score,
        )


@dataclass(frozen=True, slots=True)
class StudentVisibleOutcomeView:
    component: str
    name: str
    status: str
    earned_points: int
    possible_points: int
    detail: str | None


@dataclass(frozen=True, slots=True)
class HiddenSummaryView:
    total: int
    passed: int
    failed_or_other: int


@dataclass(frozen=True, slots=True)
class FeedbackFactView:
    kind: str
    message: str


@dataclass(frozen=True, slots=True)
class StudentResultPayload:
    score: ScoreBreakdownView
    visible_outcomes: tuple[StudentVisibleOutcomeView, ...]
    hidden_summary: HiddenSummaryView
    feedback_facts: tuple[FeedbackFactView, ...]

    @classmethod
    def from_student_view(
        cls,
        view: StudentGradingView,
    ) -> "StudentResultPayload":
        return cls(
            score=ScoreBreakdownView(
                io=WeightedComponentView(
                    weight=view.score.io.weight,
                    percentage=view.score.io.percentage,
                    contribution=view.score.io.contribution,
                ),
                unit=WeightedComponentView(
                    weight=view.score.unit.weight,
                    percentage=view.score.unit.percentage,
                    contribution=view.score.unit.contribution,
                ),
                static=WeightedComponentView(
                    weight=view.score.static.weight,
                    percentage=view.score.static.percentage,
                    contribution=view.score.static.contribution,
                ),
                final_score=view.score.final_score,
            ),
            visible_outcomes=tuple(
                StudentVisibleOutcomeView(
                    component=item.component,
                    name=item.name,
                    status=item.status,
                    earned_points=item.earned_points,
                    possible_points=item.possible_points,
                    detail=item.detail,
                )
                for item in view.visible_outcomes
            ),
            hidden_summary=HiddenSummaryView(
                total=view.hidden_summary.total,
                passed=view.hidden_summary.passed,
                failed_or_other=view.hidden_summary.failed_or_other,
            ),
            feedback_facts=tuple(
                FeedbackFactView(
                    kind=fact.kind.value,
                    message=fact.message,
                )
                for fact in view.feedback_facts
            ),
        )


@dataclass(frozen=True, slots=True)
class StudentSubmissionResultView:
    submission_id: int
    assignment_id: int
    attempt_number: int
    status: SubmissionStatus
    failure_reason: str | None
    result: StudentResultPayload | None


@dataclass(frozen=True, slots=True)
class InstructorOutcomeView:
    component: str
    name: str
    status: str
    earned_points: int
    possible_points: int
    is_hidden: bool
    detail: str | None


@dataclass(frozen=True, slots=True)
class InstructorResultPayload:
    score: ScoreBreakdownView
    outcomes: tuple[InstructorOutcomeView, ...]
    feedback_facts: tuple[FeedbackFactView, ...]

    @classmethod
    def from_result(
        cls,
        result: GradingResult,
    ) -> "InstructorResultPayload":
        return cls(
            score=ScoreBreakdownView.from_result(result),
            outcomes=tuple(
                InstructorOutcomeView(
                    component=item.component.value,
                    name=item.name,
                    status=item.status.value,
                    earned_points=item.earned_points,
                    possible_points=item.possible_points,
                    is_hidden=item.is_hidden,
                    detail=item.detail,
                )
                for item in result.outcomes
            ),
            feedback_facts=tuple(
                FeedbackFactView(
                    kind=fact.kind.value,
                    message=fact.message,
                )
                for fact in build_feedback_facts(result.outcomes)
            ),
        )


@dataclass(frozen=True, slots=True)
class InstructorSubmissionSummaryView:
    submission_id: int
    assignment_id: int
    student_id: int
    attempt_number: int
    status: SubmissionStatus
    failure_reason: str | None
    final_score: Decimal | None


@dataclass(frozen=True, slots=True)
class InstructorSubmissionResultView:
    submission_id: int
    assignment_id: int
    student_id: int
    attempt_number: int
    status: SubmissionStatus
    failure_reason: str | None
    result: InstructorResultPayload | None
