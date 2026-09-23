from __future__ import annotations

from fastapi.testclient import TestClient

from app.domain.assessment import GradingPolicy
from app.domain.grading import (
    EvaluationOutcome,
    EvaluationStatus,
    GradingComponent,
    GradingResult,
)


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


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def prepare_submission(client: TestClient) -> tuple[str, str, int, int]:
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
                b"print('ok')\n",
                "text/x-python",
            )
        },
    )
    assert response.status_code == 202
    submission_id = response.json()["id"]

    return (
        instructor_token,
        student_token,
        assignment_id,
        submission_id,
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
                name="secret edge case",
                status=EvaluationStatus.FAILED,
                earned_points=0,
                possible_points=60,
                is_hidden=True,
                detail="Secret input was -100 100.",
            ),
        ),
    )

    submission.start_grading()
    submission.complete_grading()
    grading_uow.grading_results.save(
        submission_id=submission_id,
        result=result,
    )


def test_student_can_poll_queued_submission_result(
    client: TestClient,
) -> None:
    _, student_token, _, submission_id = prepare_submission(client)

    response = client.get(
        f"/submissions/{submission_id}/result",
        headers=auth_header(student_token),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "queued"
    assert payload["result"] is None


def test_student_completed_result_hides_secret_evidence(
    client: TestClient,
    grading_uow,
) -> None:
    _, student_token, _, submission_id = prepare_submission(client)
    complete_with_result(grading_uow, submission_id)

    response = client.get(
        f"/submissions/{submission_id}/result",
        headers=auth_header(student_token),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["result"]["score"]["final_score"] == 40.0
    assert [
        item["name"]
        for item in payload["result"]["visible_outcomes"]
    ] == ["visible example"]
    assert payload["result"]["hidden_summary"] == {
        "total": 1,
        "passed": 0,
        "failed_or_other": 1,
    }
    assert "secret edge case" not in response.text
    assert "-100 100" not in response.text


def test_another_student_cannot_read_result(
    client: TestClient,
) -> None:
    _, _, _, submission_id = prepare_submission(client)
    other_student_token = register_and_login(
        client,
        email="other-student@example.com",
        role="student",
    )

    response = client.get(
        f"/submissions/{submission_id}/result",
        headers=auth_header(other_student_token),
    )

    assert response.status_code == 403


def test_instructor_list_shows_completed_score(
    client: TestClient,
    grading_uow,
) -> None:
    instructor_token, _, assignment_id, submission_id = prepare_submission(
        client
    )
    complete_with_result(grading_uow, submission_id)

    response = client.get(
        f"/assignments/{assignment_id}/submissions",
        headers=auth_header(instructor_token),
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["submission_id"] == submission_id
    assert payload[0]["status"] == "completed"
    assert payload[0]["final_score"] == 40.0


def test_instructor_detail_includes_hidden_evidence(
    client: TestClient,
    grading_uow,
) -> None:
    instructor_token, _, assignment_id, submission_id = prepare_submission(
        client
    )
    complete_with_result(grading_uow, submission_id)

    response = client.get(
        (
            f"/assignments/{assignment_id}/submissions/"
            f"{submission_id}/result"
        ),
        headers=auth_header(instructor_token),
    )

    assert response.status_code == 200
    payload = response.json()
    hidden = [
        item
        for item in payload["result"]["outcomes"]
        if item["is_hidden"]
    ]
    assert len(hidden) == 1
    assert hidden[0]["name"] == "secret edge case"
    assert hidden[0]["detail"] == "Secret input was -100 100."


def test_other_instructor_cannot_review_assignment_submissions(
    client: TestClient,
) -> None:
    _, _, assignment_id, _ = prepare_submission(client)
    other_instructor_token = register_and_login(
        client,
        email="other-teacher@example.com",
        role="instructor",
    )

    response = client.get(
        f"/assignments/{assignment_id}/submissions",
        headers=auth_header(other_instructor_token),
    )

    assert response.status_code == 403


def test_student_cannot_use_instructor_submission_review_endpoint(
    client: TestClient,
) -> None:
    _, student_token, assignment_id, _ = prepare_submission(client)

    response = client.get(
        f"/assignments/{assignment_id}/submissions",
        headers=auth_header(student_token),
    )

    assert response.status_code == 403


def test_instructor_cannot_use_student_result_endpoint(
    client: TestClient,
) -> None:
    instructor_token, _, _, submission_id = prepare_submission(client)

    response = client.get(
        f"/submissions/{submission_id}/result",
        headers=auth_header(instructor_token),
    )

    assert response.status_code == 403
