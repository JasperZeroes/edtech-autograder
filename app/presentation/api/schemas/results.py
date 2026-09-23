from __future__ import annotations

from pydantic import BaseModel

from app.application.grading import (
    InstructorSubmissionResultView,
    InstructorSubmissionSummaryView,
    StudentSubmissionResultView,
)
from app.domain.submission import SubmissionStatus


class WeightedComponentResponse(BaseModel):
    weight: int
    percentage: float
    contribution: float


class ScoreBreakdownResponse(BaseModel):
    io: WeightedComponentResponse
    unit: WeightedComponentResponse
    static: WeightedComponentResponse
    final_score: float


class FeedbackFactResponse(BaseModel):
    kind: str
    message: str


class StudentVisibleOutcomeResponse(BaseModel):
    component: str
    name: str
    status: str
    earned_points: int
    possible_points: int
    detail: str | None


class HiddenSummaryResponse(BaseModel):
    total: int
    passed: int
    failed_or_other: int


class StudentResultPayloadResponse(BaseModel):
    score: ScoreBreakdownResponse
    visible_outcomes: tuple[StudentVisibleOutcomeResponse, ...]
    hidden_summary: HiddenSummaryResponse
    feedback_facts: tuple[FeedbackFactResponse, ...]


class StudentSubmissionResultResponse(BaseModel):
    submission_id: int
    assignment_id: int
    attempt_number: int
    status: SubmissionStatus
    failure_reason: str | None
    result: StudentResultPayloadResponse | None

    @classmethod
    def from_view(
        cls,
        view: StudentSubmissionResultView,
    ) -> "StudentSubmissionResultResponse":
        payload = None
        if view.result is not None:
            payload = StudentResultPayloadResponse(
                score=ScoreBreakdownResponse(
                    io=WeightedComponentResponse(
                        weight=view.result.score.io.weight,
                        percentage=float(view.result.score.io.percentage),
                        contribution=float(view.result.score.io.contribution),
                    ),
                    unit=WeightedComponentResponse(
                        weight=view.result.score.unit.weight,
                        percentage=float(view.result.score.unit.percentage),
                        contribution=float(view.result.score.unit.contribution),
                    ),
                    static=WeightedComponentResponse(
                        weight=view.result.score.static.weight,
                        percentage=float(view.result.score.static.percentage),
                        contribution=float(view.result.score.static.contribution),
                    ),
                    final_score=float(view.result.score.final_score),
                ),
                visible_outcomes=tuple(
                    StudentVisibleOutcomeResponse(
                        component=item.component,
                        name=item.name,
                        status=item.status,
                        earned_points=item.earned_points,
                        possible_points=item.possible_points,
                        detail=item.detail,
                    )
                    for item in view.result.visible_outcomes
                ),
                hidden_summary=HiddenSummaryResponse(
                    total=view.result.hidden_summary.total,
                    passed=view.result.hidden_summary.passed,
                    failed_or_other=(
                        view.result.hidden_summary.failed_or_other
                    ),
                ),
                feedback_facts=tuple(
                    FeedbackFactResponse(
                        kind=item.kind,
                        message=item.message,
                    )
                    for item in view.result.feedback_facts
                ),
            )

        return cls(
            submission_id=view.submission_id,
            assignment_id=view.assignment_id,
            attempt_number=view.attempt_number,
            status=view.status,
            failure_reason=view.failure_reason,
            result=payload,
        )


class InstructorSubmissionSummaryResponse(BaseModel):
    submission_id: int
    assignment_id: int
    student_id: int
    attempt_number: int
    status: SubmissionStatus
    failure_reason: str | None
    final_score: float | None

    @classmethod
    def from_view(
        cls,
        view: InstructorSubmissionSummaryView,
    ) -> "InstructorSubmissionSummaryResponse":
        return cls(
            submission_id=view.submission_id,
            assignment_id=view.assignment_id,
            student_id=view.student_id,
            attempt_number=view.attempt_number,
            status=view.status,
            failure_reason=view.failure_reason,
            final_score=(
                float(view.final_score)
                if view.final_score is not None
                else None
            ),
        )


class InstructorOutcomeResponse(BaseModel):
    component: str
    name: str
    status: str
    earned_points: int
    possible_points: int
    is_hidden: bool
    detail: str | None


class InstructorResultPayloadResponse(BaseModel):
    score: ScoreBreakdownResponse
    outcomes: tuple[InstructorOutcomeResponse, ...]
    feedback_facts: tuple[FeedbackFactResponse, ...]


class InstructorSubmissionResultResponse(BaseModel):
    submission_id: int
    assignment_id: int
    student_id: int
    attempt_number: int
    status: SubmissionStatus
    failure_reason: str | None
    result: InstructorResultPayloadResponse | None

    @classmethod
    def from_view(
        cls,
        view: InstructorSubmissionResultView,
    ) -> "InstructorSubmissionResultResponse":
        payload = None
        if view.result is not None:
            payload = InstructorResultPayloadResponse(
                score=ScoreBreakdownResponse(
                    io=WeightedComponentResponse(
                        weight=view.result.score.io.weight,
                        percentage=float(view.result.score.io.percentage),
                        contribution=float(view.result.score.io.contribution),
                    ),
                    unit=WeightedComponentResponse(
                        weight=view.result.score.unit.weight,
                        percentage=float(view.result.score.unit.percentage),
                        contribution=float(view.result.score.unit.contribution),
                    ),
                    static=WeightedComponentResponse(
                        weight=view.result.score.static.weight,
                        percentage=float(view.result.score.static.percentage),
                        contribution=float(view.result.score.static.contribution),
                    ),
                    final_score=float(view.result.score.final_score),
                ),
                outcomes=tuple(
                    InstructorOutcomeResponse(
                        component=item.component,
                        name=item.name,
                        status=item.status,
                        earned_points=item.earned_points,
                        possible_points=item.possible_points,
                        is_hidden=item.is_hidden,
                        detail=item.detail,
                    )
                    for item in view.result.outcomes
                ),
                feedback_facts=tuple(
                    FeedbackFactResponse(
                        kind=item.kind,
                        message=item.message,
                    )
                    for item in view.result.feedback_facts
                ),
            )

        return cls(
            submission_id=view.submission_id,
            assignment_id=view.assignment_id,
            student_id=view.student_id,
            attempt_number=view.attempt_number,
            status=view.status,
            failure_reason=view.failure_reason,
            result=payload,
        )
