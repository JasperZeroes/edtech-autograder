from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .outcomes import EvaluationOutcome, EvaluationStatus


class FeedbackFactKind(str, Enum):
    VISIBLE_TESTS = "visible_tests"
    HIDDEN_TESTS = "hidden_tests"
    ERRORS = "errors"
    TIMEOUTS = "timeouts"


@dataclass(frozen=True, slots=True)
class FeedbackFact:
    kind: FeedbackFactKind
    message: str


def build_feedback_facts(
    outcomes: tuple[EvaluationOutcome, ...],
) -> tuple[FeedbackFact, ...]:
    visible = tuple(outcome for outcome in outcomes if not outcome.is_hidden)
    hidden = tuple(outcome for outcome in outcomes if outcome.is_hidden)

    facts: list[FeedbackFact] = []

    if visible:
        passed = sum(1 for outcome in visible if outcome.passed)
        facts.append(
            FeedbackFact(
                kind=FeedbackFactKind.VISIBLE_TESTS,
                message=f"Passed {passed} of {len(visible)} visible evaluations.",
            )
        )

    if hidden:
        passed = sum(1 for outcome in hidden if outcome.passed)
        facts.append(
            FeedbackFact(
                kind=FeedbackFactKind.HIDDEN_TESTS,
                message=f"Passed {passed} of {len(hidden)} hidden evaluations.",
            )
        )

    error_count = sum(
        1
        for outcome in outcomes
        if outcome.status is EvaluationStatus.ERROR
    )
    if error_count:
        suffix = "" if error_count == 1 else "s"
        facts.append(
            FeedbackFact(
                kind=FeedbackFactKind.ERRORS,
                message=f"{error_count} evaluation{suffix} ended with an error.",
            )
        )

    timeout_count = sum(
        1
        for outcome in outcomes
        if outcome.status is EvaluationStatus.TIMEOUT
    )
    if timeout_count:
        suffix = "" if timeout_count == 1 else "s"
        facts.append(
            FeedbackFact(
                kind=FeedbackFactKind.TIMEOUTS,
                message=f"{timeout_count} evaluation{suffix} timed out.",
            )
        )

    return tuple(facts)
