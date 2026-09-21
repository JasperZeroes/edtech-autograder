import pytest

from app.domain.assessment import (
    AssessmentValidationError,
    IOTestCase,
    StaticAnalysisRules,
    GradingTestVisibility,
    UnitTestSpecification,
)


def test_io_test_case_normalizes_name_and_defaults_to_hidden() -> None:
    test_case = IOTestCase(
        name="  adds two numbers  ",
        stdin="2 3",
        expected_stdout="5",
    )

    assert test_case.name == "adds two numbers"
    assert test_case.visibility is GradingTestVisibility.HIDDEN
    assert test_case.points == 1


@pytest.mark.parametrize(
    "kwargs",
    [
        {"name": "", "expected_stdout": "5"},
        {"name": "test", "expected_stdout": ""},
        {"name": "test", "expected_stdout": "5", "points": -1},
        {"name": "test", "expected_stdout": "5", "points": 100_001},
        {"name": "test", "expected_stdout": "5", "order_index": -1},
    ],
)
def test_invalid_io_test_case_is_rejected(kwargs: dict[str, object]) -> None:
    with pytest.raises(AssessmentValidationError):
        IOTestCase(**kwargs)  # type: ignore[arg-type]


def test_unit_test_spec_requires_non_empty_test_code() -> None:
    with pytest.raises(AssessmentValidationError):
        UnitTestSpecification(
            name="behaviour tests",
            test_code="   ",
            points=20,
        )


def test_static_rules_normalize_and_deduplicate_names() -> None:
    rules = StaticAnalysisRules(
        required_functions=(" solve ", "solve", "parse"),
        forbidden_imports=(" os ", "os"),
        max_cyclomatic_complexity=10,
        points=10,
    )

    assert rules.required_functions == ("solve", "parse")
    assert rules.forbidden_imports == ("os",)
    assert rules.has_checks is True


def test_empty_static_rule_set_has_no_checks() -> None:
    assert StaticAnalysisRules().has_checks is False


@pytest.mark.parametrize("complexity", [0, 10_001])
def test_invalid_cyclomatic_complexity_is_rejected(complexity: int) -> None:
    with pytest.raises(AssessmentValidationError):
        StaticAnalysisRules(max_cyclomatic_complexity=complexity)
