from dataclasses import FrozenInstanceError

import pytest

from app.domain.assessment import AssessmentValidationError, GradingPolicy


def test_default_grading_policy_is_70_20_10() -> None:
    policy = GradingPolicy()

    assert policy.io_weight == 70
    assert policy.unit_weight == 20
    assert policy.static_weight == 10


@pytest.mark.parametrize(
    ("io_weight", "unit_weight", "static_weight"),
    [
        (70, 20, 20),
        (50, 20, 20),
        (-1, 91, 10),
        (101, 0, -1),
    ],
)
def test_invalid_grading_distribution_is_rejected(
    io_weight: int,
    unit_weight: int,
    static_weight: int,
) -> None:
    with pytest.raises(AssessmentValidationError):
        GradingPolicy(
            io_weight=io_weight,
            unit_weight=unit_weight,
            static_weight=static_weight,
        )


def test_grading_policy_is_immutable() -> None:
    policy = GradingPolicy()

    with pytest.raises(FrozenInstanceError):
        policy.io_weight = 60  # type: ignore[misc]
