from decimal import Decimal

from app.domain.assessment import GradingPolicy
from app.domain.grading import (
    EvaluationOutcome,
    EvaluationStatus,
    GradingComponent,
    GradingResult,
)


def build_result() -> GradingResult:
    policy = GradingPolicy(
        io_weight=100,
        unit_weight=0,
        static_weight=0,
    )
    outcomes = (
        EvaluationOutcome(
            component=GradingComponent.IO,
            name="public example",
            status=EvaluationStatus.PASSED,
            earned_points=40,
            possible_points=40,
            is_hidden=False,
            detail="Expected 5 and received 5.",
        ),
        EvaluationOutcome(
            component=GradingComponent.IO,
            name="secret negative-number case",
            status=EvaluationStatus.FAILED,
            earned_points=0,
            possible_points=60,
            is_hidden=True,
            detail="Secret input was -100 100; expected 0.",
        ),
    )
    return GradingResult.build(
        policy=policy,
        outcomes=outcomes,
    )


def test_student_view_exposes_visible_outcome_details() -> None:
    view = build_result().student_view()

    assert len(view.visible_outcomes) == 1
    assert view.visible_outcomes[0].name == "public example"
    assert view.visible_outcomes[0].detail == (
        "Expected 5 and received 5."
    )


def test_student_view_aggregates_hidden_outcomes_without_details() -> None:
    view = build_result().student_view()

    assert view.hidden_summary.total == 1
    assert view.hidden_summary.passed == 0
    assert view.hidden_summary.failed_or_other == 1

    serialized = repr(view)
    assert "secret negative-number case" not in serialized
    assert "Secret input was -100 100" not in serialized
    assert "-100 100" not in serialized


def test_hidden_outcomes_still_contribute_to_deterministic_score() -> None:
    result = build_result()
    view = result.student_view()

    assert result.score.final_score == Decimal("40.00")
    assert view.score.final_score == Decimal("40.00")


def test_feedback_facts_do_not_leak_hidden_names_or_details() -> None:
    view = build_result().student_view()

    serialized = " ".join(
        fact.message for fact in view.feedback_facts
    )

    assert "secret negative-number case" not in serialized
    assert "-100 100" not in serialized
    assert "Passed 0 of 1 hidden evaluations." in serialized
