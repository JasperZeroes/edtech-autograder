from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.domain.submission import SubmissionStatus

from .errors import (
    AIFeedbackNotReadyError,
    AIFeedbackProtocolError,
    GradingResultMissingError,
    GradingSubmissionNotFoundError,
    ResultAccessError,
)
from .ports import AIFeedbackGateway, GradingUnitOfWork


@dataclass(frozen=True, slots=True)
class AIFeedbackRequest:
    """Student-safe facts supplied to an advisory AI provider.

    Intentionally excludes raw source code and hidden-test identities/details.
    """

    submission_id: int
    final_score: Decimal
    io_percentage: Decimal
    unit_percentage: Decimal
    static_percentage: Decimal
    visible_outcomes: tuple[str, ...]
    hidden_total: int
    hidden_passed: int
    hidden_failed_or_other: int
    deterministic_facts: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AIFeedbackSuggestion:
    submission_id: int
    suggestion: str
    advisory: str = (
        "AI-generated learning suggestion. "
        "It does not affect the authoritative grade."
    )


class GenerateStudentAISuggestion:
    def __init__(
        self,
        *,
        unit_of_work: GradingUnitOfWork,
        feedback_gateway: AIFeedbackGateway,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._feedback_gateway = feedback_gateway

    def execute(
        self,
        *,
        submission_id: int,
        student_id: int,
    ) -> AIFeedbackSuggestion:
        submission = self._unit_of_work.submissions.get_by_id(submission_id)
        if submission is None:
            raise GradingSubmissionNotFoundError(
                f"Submission {submission_id} was not found."
            )

        if submission.student_id != student_id:
            raise ResultAccessError(
                "Students may request AI suggestions only for "
                "their own submissions."
            )

        if submission.status is not SubmissionStatus.COMPLETED:
            raise AIFeedbackNotReadyError(
                "AI suggestions are available only after grading completes."
            )

        stored = self._unit_of_work.grading_results.get_by_submission_id(
            submission_id
        )
        if stored is None:
            raise GradingResultMissingError(
                f"Completed submission {submission_id} has no grading result."
            )

        student_view = stored.result.student_view()

        request = AIFeedbackRequest(
            submission_id=submission_id,
            final_score=student_view.score.final_score,
            io_percentage=student_view.score.io.percentage,
            unit_percentage=student_view.score.unit.percentage,
            static_percentage=student_view.score.static.percentage,
            visible_outcomes=tuple(
                (
                    f"{item.component}: {item.name}: {item.status}; "
                    f"{item.earned_points}/{item.possible_points} points"
                    + (f"; {item.detail}" if item.detail else "")
                )
                for item in student_view.visible_outcomes
            ),
            hidden_total=student_view.hidden_summary.total,
            hidden_passed=student_view.hidden_summary.passed,
            hidden_failed_or_other=(
                student_view.hidden_summary.failed_or_other
            ),
            deterministic_facts=tuple(
                fact.message for fact in student_view.feedback_facts
            ),
        )

        suggestion = self._feedback_gateway.generate(request).strip()
        if not suggestion:
            raise AIFeedbackProtocolError(
                "AI feedback gateway returned an empty suggestion."
            )

        return AIFeedbackSuggestion(
            submission_id=submission_id,
            suggestion=suggestion,
        )
