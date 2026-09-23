from __future__ import annotations

from fastapi.testclient import TestClient

from app.application.grading import AIFeedbackUnavailableError
from app.domain.assessment import GradingPolicy
from app.domain.grading import (
    EvaluationOutcome,
    EvaluationStatus,
    GradingComponent,
    GradingResult,
)
from app.main import app
from app.presentation.api.dependencies import get_ai_feedback_gateway


class CapturingGateway:
    def __init__(
        self,
        *,
        suggestion: str = (
            "1. Revisit boundary cases.\n"
            "2. Add focused local tests.\n"
            "3. Review the visible failure pattern."
        ),
    ) -> None:
        self.suggestion = suggestion
        self.requests = []

    def generate(self, request):
        self.requests.append(request)
        return self.suggestion


class UnavailableGateway:
    def generate(self, request):
        raise AIFeedbackUnavailableError("AI provider unavailable.")


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


def prepare_submission(
    client: TestClient,
) -> tuple[str, str, int, int]:
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

    response = client.post(
        "/assignments",
        headers=auth_header(instructor_token),
        json={
            "title": "Python Basics",
            "description": "Complete the exercise.",
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
                    "name": "basic",
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

    response = client.post(
        f"/assignments/{assignment_id}/submissions",
        headers=auth_header(student_token),
        files={
            "file": (
                "solution.py",
                b"secret_source_marker = 123\nprint('ok')\n",
                "text/x-python",
            )
        },
    )
    assert response.status_code == 202

    return (
        instructor_token,
        student_token,
        assignment_id,
        response.json()["id"],
    )


def complete_with_result(grading_uow, submission_id: int) -> None:
    submission = grading_uow.submissions.get_by_id(submission_id)
    assert submission is not None

    result = GradingResult.build(
        policy=GradingPolicy(
            io_weight=100,
            unit_weight=0,
            static_weight=0,
        ),
        outcomes=(
            EvaluationOutcome(
                component=GradingComponent.IO,
                name="visible example",
                status=EvaluationStatus.PASSED,
                earned_points=40,
                possible_points=40,
                is_hidden=False,
                detail="Visible diagnostic.",
            ),
            EvaluationOutcome(
                component=GradingComponent.IO,
                name="secret hidden case",
                status=EvaluationStatus.FAILED,
                earned_points=0,
                possible_points=60,
                is_hidden=True,
                detail="secret input -100 100 expected 0",
            ),
        ),
    )

    submission.start_grading()
    submission.complete_grading()
    grading_uow.grading_results.save(
        submission_id=submission_id,
        result=result,
    )


def test_completed_student_can_request_advisory_ai_feedback(
    client: TestClient,
    grading_uow,
) -> None:
    _, student_token, _, submission_id = prepare_submission(client)
    complete_with_result(grading_uow, submission_id)

    gateway = CapturingGateway()
    app.dependency_overrides[get_ai_feedback_gateway] = lambda: gateway

    response = client.post(
        f"/submissions/{submission_id}/ai-feedback",
        headers=auth_header(student_token),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["submission_id"] == submission_id
    assert "Revisit boundary cases" in payload["suggestion"]
    assert "does not affect" in payload["advisory"]

    serialized_request = repr(gateway.requests[0])
    assert "visible example" in serialized_request
    assert "secret hidden case" not in serialized_request
    assert "-100 100" not in serialized_request
    assert "secret_source_marker" not in serialized_request

    result_response = client.get(
        f"/submissions/{submission_id}/result",
        headers=auth_header(student_token),
    )
    assert result_response.status_code == 200
    assert result_response.json()["result"]["score"]["final_score"] == 40.0


def test_ai_feedback_before_grading_completion_returns_409(
    client: TestClient,
) -> None:
    _, student_token, _, submission_id = prepare_submission(client)
    gateway = CapturingGateway()
    app.dependency_overrides[get_ai_feedback_gateway] = lambda: gateway

    response = client.post(
        f"/submissions/{submission_id}/ai-feedback",
        headers=auth_header(student_token),
    )

    assert response.status_code == 409
    assert gateway.requests == []


def test_ai_provider_outage_returns_503_without_losing_grade(
    client: TestClient,
    grading_uow,
) -> None:
    _, student_token, _, submission_id = prepare_submission(client)
    complete_with_result(grading_uow, submission_id)
    app.dependency_overrides[get_ai_feedback_gateway] = (
        lambda: UnavailableGateway()
    )

    response = client.post(
        f"/submissions/{submission_id}/ai-feedback",
        headers=auth_header(student_token),
    )

    assert response.status_code == 503

    result_response = client.get(
        f"/submissions/{submission_id}/result",
        headers=auth_header(student_token),
    )
    assert result_response.status_code == 200
    assert result_response.json()["status"] == "completed"
    assert result_response.json()["result"]["score"]["final_score"] == 40.0


def test_instructor_cannot_request_student_ai_feedback(
    client: TestClient,
    grading_uow,
) -> None:
    instructor_token, _, _, submission_id = prepare_submission(client)
    complete_with_result(grading_uow, submission_id)
    app.dependency_overrides[get_ai_feedback_gateway] = (
        lambda: CapturingGateway()
    )

    response = client.post(
        f"/submissions/{submission_id}/ai-feedback",
        headers=auth_header(instructor_token),
    )

    assert response.status_code == 403
