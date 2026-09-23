from __future__ import annotations

from fastapi.testclient import TestClient

import pytest

from app.application.grading import (
    CodeExecutionRequest,
    CodeExecutionUnavailableError,
    GradeSubmission,
)
from app.application.grading.requests import SourceAnalysisReport
from app.domain.grading import EvaluationStatus, ExecutionOutcome
from app.infrastructure.grading import PythonSourceAnalyzer
from tests.application.submission.fakes import FakeGradingQueue


class SequenceExecutionGateway:
    def __init__(
        self,
        outcomes: list[ExecutionOutcome],
    ) -> None:
        self._outcomes = list(outcomes)
        self.requests: list[CodeExecutionRequest] = []

    def execute(self, request: CodeExecutionRequest) -> ExecutionOutcome:
        self.requests.append(request)
        if not self._outcomes:
            raise AssertionError("No execution outcome configured.")
        return self._outcomes.pop(0)


class FailingExecutionGateway:
    def execute(self, request: CodeExecutionRequest) -> ExecutionOutcome:
        raise CodeExecutionUnavailableError("Judge0 is unavailable.")


class PassingSourceAnalyzer:
    def analyze(self, *, source_code: str, rules) -> SourceAnalysisReport:
        return SourceAnalysisReport(
            syntax_valid=True,
            missing_required_functions=(),
            forbidden_imports_found=(),
            observed_max_cyclomatic_complexity=1,
            max_cyclomatic_complexity_allowed=(
                rules.max_cyclomatic_complexity
            ),
        )


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def register_and_login(
    client: TestClient,
    *,
    email: str,
    role: str,
) -> str:
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "password123",
            "role": role,
            "full_name": f"{role.title()} User",
        },
    )
    assert response.status_code == 201

    response = client.post(
        "/auth/login",
        data={
            "username": email,
            "password": "password123",
        },
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def create_full_assignment(
    client: TestClient,
    *,
    instructor_token: str,
) -> int:
    response = client.post(
        "/assignments",
        headers=auth_header(instructor_token),
        json={
            "title": "Functions and Control Flow",
            "description": "Implement solve(a, b).",
            "instructions": "Read two integers and print their sum.",
            "grading_policy": {
                "io_weight": 70,
                "unit_weight": 20,
                "static_weight": 10,
            },
            "execution_limits": {
                "max_runtime_ms": 2000,
                "max_memory_kb": 128000,
            },
        },
    )
    assert response.status_code == 201
    assignment_id = response.json()["id"]

    response = client.patch(
        f"/assignments/{assignment_id}/configuration",
        headers=auth_header(instructor_token),
        json={
            "io_test_cases": [
                {
                    "name": "visible example",
                    "stdin": "2 3",
                    "expected_stdout": "5",
                    "points": 40,
                    "visibility": "visible",
                    "order_index": 1,
                },
                {
                    "name": "hidden edge",
                    "stdin": "-1 1",
                    "expected_stdout": "0",
                    "points": 30,
                    "visibility": "hidden",
                    "order_index": 2,
                },
            ],
            "unit_test_spec": {
                "name": "hidden unit tests",
                "test_code": "assert solve(2, 3) == 5",
                "points": 20,
                "visibility": "hidden",
            },
            "static_analysis_rules": {
                "required_functions": ["solve"],
                "forbidden_imports": ["os"],
                "max_cyclomatic_complexity": 10,
                "points": 10,
            },
        },
    )
    assert response.status_code == 200

    response = client.post(
        f"/assignments/{assignment_id}/publish",
        headers=auth_header(instructor_token),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "published"

    return assignment_id


def create_io_only_assignment(
    client: TestClient,
    *,
    instructor_token: str,
) -> int:
    response = client.post(
        "/assignments",
        headers=auth_header(instructor_token),
        json={
            "title": "Simple Output",
            "description": "Print ok.",
            "grading_policy": {
                "io_weight": 100,
                "unit_weight": 0,
                "static_weight": 0,
            },
        },
    )
    assert response.status_code == 201
    assignment_id = response.json()["id"]

    response = client.patch(
        f"/assignments/{assignment_id}/configuration",
        headers=auth_header(instructor_token),
        json={
            "io_test_cases": [
                {
                    "name": "output",
                    "expected_stdout": "ok",
                    "points": 100,
                    "visibility": "hidden",
                }
            ]
        },
    )
    assert response.status_code == 200

    response = client.post(
        f"/assignments/{assignment_id}/publish",
        headers=auth_header(instructor_token),
    )
    assert response.status_code == 200

    return assignment_id


def submit_solution(
    client: TestClient,
    *,
    student_token: str,
    assignment_id: int,
    source: bytes = (
        b"def solve(a, b):\n"
        b"    return a + b\n"
        b"a, b = map(int, input().split())\n"
        b"print(solve(a, b))\n"
    ),
):
    return client.post(
        f"/assignments/{assignment_id}/submissions",
        headers=auth_header(student_token),
        files={
            "file": (
                "solution.py",
                source,
                "text/x-python",
            )
        },
    )


def test_complete_user_journey_from_authoring_to_results(
    client: TestClient,
    grading_uow,
    grading_queue: FakeGradingQueue,
) -> None:
    instructor_token = register_and_login(
        client,
        email="teacher@example.com",
        role="instructor",
    )
    student_token = register_and_login(
        client,
        email="student@example.com",
        role="student",
    )

    assignment_id = create_full_assignment(
        client,
        instructor_token=instructor_token,
    )

    published = client.get(
        f"/assignments/{assignment_id}",
        headers=auth_header(student_token),
    )
    assert published.status_code == 200
    assert published.json()["visible_io_examples"][0]["name"] == (
        "visible example"
    )
    assert published.json()["visible_unit_test"] is None
    assert "hidden edge" not in published.text
    assert "-1 1" not in published.text
    assert "assert solve(2, 3) == 5" not in published.text

    submitted = submit_solution(
        client,
        student_token=student_token,
        assignment_id=assignment_id,
    )
    assert submitted.status_code == 202
    submission_id = submitted.json()["id"]
    assert grading_queue.enqueued == [submission_id]

    queued = client.get(
        f"/submissions/{submission_id}/result",
        headers=auth_header(student_token),
    )
    assert queued.status_code == 200
    assert queued.json()["status"] == "queued"
    assert queued.json()["result"] is None

    gateway = SequenceExecutionGateway(
        [
            ExecutionOutcome(
                status=EvaluationStatus.PASSED,
                stdout="5\n",
                runtime_ms=12,
            ),
            ExecutionOutcome(
                status=EvaluationStatus.PASSED,
                stdout="999\n",
                runtime_ms=11,
            ),
            ExecutionOutcome(
                status=EvaluationStatus.PASSED,
                runtime_ms=8,
            ),
        ]
    )

    graded = GradeSubmission(
        unit_of_work=grading_uow,
        execution_gateway=gateway,
        source_analyzer=PythonSourceAnalyzer(),
    ).execute(submission_id=submission_id)

    assert graded.stored_result.result.score.final_score == 70

    student_result = client.get(
        f"/submissions/{submission_id}/result",
        headers=auth_header(student_token),
    )
    assert student_result.status_code == 200
    payload = student_result.json()
    assert payload["status"] == "completed"
    assert payload["result"]["score"]["final_score"] == 70.0
    assert payload["result"]["hidden_summary"] == {
        "total": 2,
        "passed": 1,
        "failed_or_other": 1,
    }
    assert "hidden edge" not in student_result.text
    assert "hidden unit tests" not in student_result.text
    assert "-1 1" not in student_result.text
    assert "assert solve(2, 3) == 5" not in student_result.text

    instructor_result = client.get(
        (
            f"/assignments/{assignment_id}/submissions/"
            f"{submission_id}/result"
        ),
        headers=auth_header(instructor_token),
    )
    assert instructor_result.status_code == 200
    instructor_payload = instructor_result.json()
    hidden_names = {
        item["name"]
        for item in instructor_payload["result"]["outcomes"]
        if item["is_hidden"]
    }
    assert hidden_names == {"hidden edge", "hidden unit tests"}


def test_repeated_submissions_create_independent_attempts(
    client: TestClient,
    grading_queue: FakeGradingQueue,
) -> None:
    instructor_token = register_and_login(
        client,
        email="teacher@example.com",
        role="instructor",
    )
    student_token = register_and_login(
        client,
        email="student@example.com",
        role="student",
    )
    assignment_id = create_io_only_assignment(
        client,
        instructor_token=instructor_token,
    )

    first = submit_solution(
        client,
        student_token=student_token,
        assignment_id=assignment_id,
        source=b"print('first')\n",
    )
    second = submit_solution(
        client,
        student_token=student_token,
        assignment_id=assignment_id,
        source=b"print('second')\n",
    )

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["attempt_number"] == 1
    assert second.json()["attempt_number"] == 2
    assert first.json()["id"] != second.json()["id"]
    assert grading_queue.enqueued == [
        first.json()["id"],
        second.json()["id"],
    ]

    mine = client.get(
        "/submissions/mine",
        headers=auth_header(student_token),
    )
    assert mine.status_code == 200
    assert [item["attempt_number"] for item in mine.json()] == [1, 2]


def test_student_timeout_produces_completed_zero_score_not_platform_failure(
    client: TestClient,
    grading_uow,
) -> None:
    instructor_token = register_and_login(
        client,
        email="teacher@example.com",
        role="instructor",
    )
    student_token = register_and_login(
        client,
        email="student@example.com",
        role="student",
    )
    assignment_id = create_io_only_assignment(
        client,
        instructor_token=instructor_token,
    )
    submitted = submit_solution(
        client,
        student_token=student_token,
        assignment_id=assignment_id,
        source=b"while True:\n    pass\n",
    )
    assert submitted.status_code == 202
    submission_id = submitted.json()["id"]

    GradeSubmission(
        unit_of_work=grading_uow,
        execution_gateway=SequenceExecutionGateway(
            [ExecutionOutcome(status=EvaluationStatus.TIMEOUT)]
        ),
        source_analyzer=PassingSourceAnalyzer(),
    ).execute(submission_id=submission_id)

    result = client.get(
        f"/submissions/{submission_id}/result",
        headers=auth_header(student_token),
    )
    assert result.status_code == 200
    assert result.json()["status"] == "completed"
    assert result.json()["result"]["score"]["final_score"] == 0.0
    messages = [
        item["message"]
        for item in result.json()["result"]["feedback_facts"]
    ]
    assert "1 evaluation timed out." in messages


def test_execution_service_failure_marks_submission_failed_without_grade(
    client: TestClient,
    grading_uow,
) -> None:
    instructor_token = register_and_login(
        client,
        email="teacher@example.com",
        role="instructor",
    )
    student_token = register_and_login(
        client,
        email="student@example.com",
        role="student",
    )
    assignment_id = create_io_only_assignment(
        client,
        instructor_token=instructor_token,
    )
    submitted = submit_solution(
        client,
        student_token=student_token,
        assignment_id=assignment_id,
        source=b"print('ok')\n",
    )
    submission_id = submitted.json()["id"]

    with pytest.raises(CodeExecutionUnavailableError):
        GradeSubmission(
            unit_of_work=grading_uow,
            execution_gateway=FailingExecutionGateway(),
            source_analyzer=PassingSourceAnalyzer(),
        ).execute(submission_id=submission_id)

    result = client.get(
        f"/submissions/{submission_id}/result",
        headers=auth_header(student_token),
    )
    assert result.status_code == 200
    assert result.json()["status"] == "failed"
    assert result.json()["failure_reason"] == "Execution service failure."
    assert result.json()["result"] is None


def test_queue_failure_returns_503_but_preserves_submission(
    client: TestClient,
    grading_queue: FakeGradingQueue,
) -> None:
    instructor_token = register_and_login(
        client,
        email="teacher@example.com",
        role="instructor",
    )
    student_token = register_and_login(
        client,
        email="student@example.com",
        role="student",
    )
    assignment_id = create_io_only_assignment(
        client,
        instructor_token=instructor_token,
    )
    grading_queue.fail_on_enqueue = True

    submitted = submit_solution(
        client,
        student_token=student_token,
        assignment_id=assignment_id,
        source=b"print('ok')\n",
    )

    assert submitted.status_code == 503
    assert submitted.headers["retry-after"] == "5"

    mine = client.get(
        "/submissions/mine",
        headers=auth_header(student_token),
    )
    assert mine.status_code == 200
    assert len(mine.json()) == 1
    assert mine.json()[0]["status"] == "queued"


def test_result_and_review_authorization_boundaries_hold_end_to_end(
    client: TestClient,
) -> None:
    instructor_token = register_and_login(
        client,
        email="teacher@example.com",
        role="instructor",
    )
    student_token = register_and_login(
        client,
        email="student@example.com",
        role="student",
    )
    other_student_token = register_and_login(
        client,
        email="other-student@example.com",
        role="student",
    )
    other_instructor_token = register_and_login(
        client,
        email="other-teacher@example.com",
        role="instructor",
    )
    assignment_id = create_io_only_assignment(
        client,
        instructor_token=instructor_token,
    )
    submitted = submit_solution(
        client,
        student_token=student_token,
        assignment_id=assignment_id,
        source=b"print('ok')\n",
    )
    submission_id = submitted.json()["id"]

    unauthenticated = client.get(
        f"/submissions/{submission_id}/result"
    )
    assert unauthenticated.status_code == 401

    cross_student = client.get(
        f"/submissions/{submission_id}/result",
        headers=auth_header(other_student_token),
    )
    assert cross_student.status_code == 403

    cross_instructor = client.get(
        f"/assignments/{assignment_id}/submissions",
        headers=auth_header(other_instructor_token),
    )
    assert cross_instructor.status_code == 403

    wrong_role = client.get(
        f"/assignments/{assignment_id}/submissions",
        headers=auth_header(student_token),
    )
    assert wrong_role.status_code == 403
