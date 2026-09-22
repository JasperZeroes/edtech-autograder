from app.domain.grading import (
    EvaluationOutcome,
    EvaluationStatus,
    FeedbackFactKind,
    GradingComponent,
    build_feedback_facts,
)


def test_feedback_facts_are_deterministic_aggregates() -> None:
    outcomes = (
        EvaluationOutcome(
            component=GradingComponent.IO,
            name="visible pass",
            status=EvaluationStatus.PASSED,
            earned_points=10,
            possible_points=10,
            is_hidden=False,
        ),
        EvaluationOutcome(
            component=GradingComponent.IO,
            name="visible fail",
            status=EvaluationStatus.FAILED,
            earned_points=0,
            possible_points=10,
            is_hidden=False,
        ),
        EvaluationOutcome(
            component=GradingComponent.UNIT,
            name="secret case",
            status=EvaluationStatus.PASSED,
            earned_points=10,
            possible_points=10,
            is_hidden=True,
        ),
    )

    facts = build_feedback_facts(outcomes)

    assert facts[0].kind is FeedbackFactKind.VISIBLE_TESTS
    assert facts[0].message == "Passed 1 of 2 visible evaluations."
    assert facts[1].kind is FeedbackFactKind.HIDDEN_TESTS
    assert facts[1].message == "Passed 1 of 1 hidden evaluations."


def test_feedback_reports_errors_and_timeouts_without_interpretation() -> None:
    outcomes = (
        EvaluationOutcome(
            component=GradingComponent.IO,
            name="runtime failure",
            status=EvaluationStatus.ERROR,
            earned_points=0,
            possible_points=10,
        ),
        EvaluationOutcome(
            component=GradingComponent.IO,
            name="slow case",
            status=EvaluationStatus.TIMEOUT,
            earned_points=0,
            possible_points=10,
        ),
    )

    facts = build_feedback_facts(outcomes)

    assert any(
        fact.kind is FeedbackFactKind.ERRORS
        and fact.message == "1 evaluation ended with an error."
        for fact in facts
    )
    assert any(
        fact.kind is FeedbackFactKind.TIMEOUTS
        and fact.message == "1 evaluation timed out."
        for fact in facts
    )
