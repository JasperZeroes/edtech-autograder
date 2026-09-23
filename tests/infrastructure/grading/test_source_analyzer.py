from app.domain.assessment import StaticAnalysisRules
from app.infrastructure.grading import PythonSourceAnalyzer


def analyze(
    source_code: str,
    *,
    required_functions: tuple[str, ...] = (),
    forbidden_imports: tuple[str, ...] = (),
    max_complexity: int | None = None,
):
    return PythonSourceAnalyzer().analyze(
        source_code=source_code,
        rules=StaticAnalysisRules(
            required_functions=required_functions,
            forbidden_imports=forbidden_imports,
            max_cyclomatic_complexity=max_complexity,
            points=10,
        ),
    )


def test_required_functions_are_discovered_with_ast() -> None:
    report = analyze(
        """
def solve(value):
    return value * 2

async def fetch():
    return 1
""",
        required_functions=("solve", "fetch"),
    )

    assert report.syntax_valid is True
    assert report.missing_required_functions == ()
    assert report.passed is True


def test_missing_required_functions_are_reported() -> None:
    report = analyze(
        "def helper():\n    return 1\n",
        required_functions=("solve", "helper"),
    )

    assert report.missing_required_functions == ("solve",)
    assert report.passed is False


def test_direct_forbidden_import_is_detected() -> None:
    report = analyze(
        "import os\nimport json\n",
        forbidden_imports=("os",),
    )

    assert report.forbidden_imports_found == ("os",)
    assert report.passed is False


def test_forbidden_import_from_submodule_is_detected() -> None:
    report = analyze(
        "from os.path import join\n",
        forbidden_imports=("os",),
    )

    assert report.forbidden_imports_found == ("os",)


def test_unrelated_import_is_allowed() -> None:
    report = analyze(
        "import json\n",
        forbidden_imports=("os", "subprocess"),
    )

    assert report.forbidden_imports_found == ()
    assert report.passed is True


def test_complexity_is_measured_with_radon() -> None:
    report = analyze(
        """
def solve(value):
    if value > 10:
        return 1
    elif value > 5:
        return 2
    return 3
""",
        max_complexity=2,
    )

    assert report.observed_max_cyclomatic_complexity is not None
    assert report.observed_max_cyclomatic_complexity > 2
    assert report.complexity_within_limit is False
    assert report.passed is False


def test_complexity_passes_when_within_limit() -> None:
    report = analyze(
        "def solve(value):\n    return value * 2\n",
        max_complexity=5,
    )

    assert report.observed_max_cyclomatic_complexity == 1
    assert report.complexity_within_limit is True
    assert report.passed is True


def test_syntax_error_is_reported_without_executing_source() -> None:
    report = analyze(
        "def solve(:\n    pass\n",
        required_functions=("solve",),
        forbidden_imports=("os",),
        max_complexity=5,
    )

    assert report.syntax_valid is False
    assert report.syntax_error is not None
    assert "line 1" in report.syntax_error
    assert report.missing_required_functions == ("solve",)
    assert report.forbidden_imports_found == ()
    assert report.passed is False


def test_top_level_code_is_analyzed_but_never_executed() -> None:
    report = analyze(
        """
raise RuntimeError("this must never execute")

def solve():
    return 1
""",
        required_functions=("solve",),
    )

    assert report.syntax_valid is True
    assert report.missing_required_functions == ()
    assert report.passed is True
