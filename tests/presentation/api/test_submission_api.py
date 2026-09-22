from __future__ import annotations

from fastapi.testclient import TestClient

from tests.application.submission.fakes import (
    FakeGradingQueue,
    FakeSubmissionUnitOfWork,
)


def register_and_login(
    client: TestClient,
    *,
    email: str,
    role: str,
) -> str:
    register_response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "password123",
            "role": role,
            "full_name": f"{role.title()} User",
        },
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        data={
            "username": email,
            "password": "password123",
        },
    )
    assert login_response.status_code == 200
    return login_response.json()["access_token"]


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_assignment(
    client: TestClient,
    instructor_token: str,
) -> int:
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
    return response.json()["id"]


def configure_and_publish(
    client: TestClient,
    instructor_token: str,
    assignment_id: int,
) -> None:
    configure_response = client.patch(
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
    assert configure_response.status_code == 200

    publish_response = client.post(
        f"/assignments/{assignment_id}/publish",
        headers=auth_header(instructor_token),
    )
    assert publish_response.status_code == 200


def prepare_published_assignment(
    client: TestClient,
) -> tuple[str, str, int]:
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
    assignment_id = create_assignment(client, instructor_token)
    configure_and_publish(
        client,
        instructor_token,
        assignment_id,
    )
    return instructor_token, student_token, assignment_id


def upload_python(
    client: TestClient,
    *,
    token: str,
    assignment_id: int,
    content: bytes = b"print('hello')\n",
    filename: str = "solution.py",
    content_type: str = "text/x-python",
):
    return client.post(
        f"/assignments/{assignment_id}/submissions",
        headers=auth_header(token),
        files={
            "file": (
                filename,
                content,
                content_type,
            )
        },
    )


def test_student_can_upload_python_submission(
    client: TestClient,
    grading_queue: FakeGradingQueue,
) -> None:
    _, student_token, assignment_id = prepare_published_assignment(client)

    response = upload_python(
        client,
        token=student_token,
        assignment_id=assignment_id,
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["assignment_id"] == assignment_id
    assert payload["attempt_number"] == 1
    assert payload["status"] == "queued"
    assert payload["source_code"] == "print('hello')\n"
    assert grading_queue.enqueued == [payload["id"]]


def test_repeated_uploads_create_separate_attempts(
    client: TestClient,
) -> None:
    _, student_token, assignment_id = prepare_published_assignment(client)

    first = upload_python(
        client,
        token=student_token,
        assignment_id=assignment_id,
        content=b"print('first')\n",
    )
    second = upload_python(
        client,
        token=student_token,
        assignment_id=assignment_id,
        content=b"print('second')\n",
    )

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["attempt_number"] == 1
    assert second.json()["attempt_number"] == 2
    assert first.json()["id"] != second.json()["id"]


def test_submission_requires_student_role(client: TestClient) -> None:
    instructor_token = register_and_login(
        client,
        email="teacher@example.com",
        role="instructor",
    )
    assignment_id = create_assignment(client, instructor_token)
    configure_and_publish(client, instructor_token, assignment_id)

    response = upload_python(
        client,
        token=instructor_token,
        assignment_id=assignment_id,
    )

    assert response.status_code == 403


def test_submission_requires_authentication(client: TestClient) -> None:
    response = client.post(
        "/assignments/1/submissions",
        files={
            "file": (
                "solution.py",
                b"print('hello')",
                "text/x-python",
            )
        },
    )

    assert response.status_code == 401


def test_student_cannot_submit_to_draft_assignment(
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
    assignment_id = create_assignment(client, instructor_token)

    response = upload_python(
        client,
        token=student_token,
        assignment_id=assignment_id,
    )

    assert response.status_code == 404


def test_only_python_file_extension_is_accepted(
    client: TestClient,
) -> None:
    _, student_token, assignment_id = prepare_published_assignment(client)

    response = upload_python(
        client,
        token=student_token,
        assignment_id=assignment_id,
        filename="solution.txt",
        content_type="text/plain",
    )

    assert response.status_code == 415
    assert response.json()["detail"] == "Only .py source files are accepted."


def test_unsupported_content_type_is_rejected(
    client: TestClient,
) -> None:
    _, student_token, assignment_id = prepare_published_assignment(client)

    response = upload_python(
        client,
        token=student_token,
        assignment_id=assignment_id,
        content_type="image/png",
    )

    assert response.status_code == 415


def test_oversized_source_file_is_rejected(
    client: TestClient,
) -> None:
    _, student_token, assignment_id = prepare_published_assignment(client)

    response = upload_python(
        client,
        token=student_token,
        assignment_id=assignment_id,
        content=b"x" * (256 * 1024 + 1),
    )

    assert response.status_code == 413
    assert "256 KiB" in response.json()["detail"]


def test_source_file_must_be_valid_utf8(client: TestClient) -> None:
    _, student_token, assignment_id = prepare_published_assignment(client)

    response = upload_python(
        client,
        token=student_token,
        assignment_id=assignment_id,
        content=b"\xff\xfe\xfd",
    )

    assert response.status_code == 422
    assert "UTF-8" in response.json()["detail"]


def test_blank_python_source_is_rejected(client: TestClient) -> None:
    _, student_token, assignment_id = prepare_published_assignment(client)

    response = upload_python(
        client,
        token=student_token,
        assignment_id=assignment_id,
        content=b"   \n\t",
    )

    assert response.status_code == 422
    assert "must not be empty" in response.json()["detail"]


def test_list_my_submissions_returns_summary_without_source_code(
    client: TestClient,
) -> None:
    _, student_token, assignment_id = prepare_published_assignment(client)

    upload_python(
        client,
        token=student_token,
        assignment_id=assignment_id,
    )

    response = client.get(
        "/submissions/mine",
        headers=auth_header(student_token),
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["attempt_number"] == 1
    assert "source_code" not in payload[0]
    assert "student_id" not in payload[0]


def test_student_can_retrieve_own_submission_detail(
    client: TestClient,
) -> None:
    _, student_token, assignment_id = prepare_published_assignment(client)

    created = upload_python(
        client,
        token=student_token,
        assignment_id=assignment_id,
    ).json()

    response = client.get(
        f"/submissions/{created['id']}",
        headers=auth_header(student_token),
    )

    assert response.status_code == 200
    assert response.json()["source_code"] == "print('hello')\n"
    assert response.json()["student_id"] == 2


def test_student_cannot_retrieve_another_students_submission(
    client: TestClient,
) -> None:
    _, first_student_token, assignment_id = prepare_published_assignment(client)

    created = upload_python(
        client,
        token=first_student_token,
        assignment_id=assignment_id,
    ).json()

    second_student_token = register_and_login(
        client,
        email="second-student@example.com",
        role="student",
    )

    response = client.get(
        f"/submissions/{created['id']}",
        headers=auth_header(second_student_token),
    )

    assert response.status_code == 403


def test_queue_failure_returns_503_but_submission_remains_persisted(
    client: TestClient,
    grading_queue: FakeGradingQueue,
    submission_uow: FakeSubmissionUnitOfWork,
) -> None:
    _, student_token, assignment_id = prepare_published_assignment(client)
    grading_queue.fail_on_enqueue = True

    response = upload_python(
        client,
        token=student_token,
        assignment_id=assignment_id,
    )

    assert response.status_code == 503
    assert response.headers["retry-after"] == "5"
    assert "was saved but could not be queued" in response.json()["detail"]

    persisted = submission_uow.submissions.get_by_id(1)
    assert persisted is not None
    assert persisted.attempt_number == 1
    assert submission_uow.committed is True
    assert submission_uow.rolled_back is False
