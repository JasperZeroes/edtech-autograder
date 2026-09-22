from __future__ import annotations

from fastapi.testclient import TestClient


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
    *,
    title: str = "Functions and Control Flow",
) -> dict[str, object]:
    response = client.post(
        "/assignments",
        headers=auth_header(instructor_token),
        json={
            "title": title,
            "description": "Implement the required Python functions.",
            "instructions": "Submit one Python file.",
        },
    )
    assert response.status_code == 201
    return response.json()


def configure_complete_assignment(
    client: TestClient,
    instructor_token: str,
    assignment_id: int,
) -> dict[str, object]:
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
                    "name": "hidden edge case",
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
    return response.json()


def publish_assignment(
    client: TestClient,
    instructor_token: str,
    assignment_id: int,
) -> dict[str, object]:
    response = client.post(
        f"/assignments/{assignment_id}/publish",
        headers=auth_header(instructor_token),
    )
    assert response.status_code == 200
    return response.json()


def test_instructor_can_create_assignment(client: TestClient) -> None:
    token = register_and_login(
        client,
        email="teacher@example.com",
        role="instructor",
    )

    payload = create_assignment(client, token)

    assert payload["id"] == 1
    assert payload["instructor_id"] == 1
    assert payload["title"] == "Functions and Control Flow"
    assert payload["status"] == "draft"
    assert payload["io_weight"] == 70
    assert payload["unit_weight"] == 20
    assert payload["static_weight"] == 10


def test_student_cannot_create_assignment(client: TestClient) -> None:
    token = register_and_login(
        client,
        email="student@example.com",
        role="student",
    )

    response = client.post(
        "/assignments",
        headers=auth_header(token),
        json={
            "title": "Unauthorized Assignment",
            "description": "Students cannot author assignments.",
        },
    )

    assert response.status_code == 403


def test_create_assignment_rejects_invalid_weight_total(
    client: TestClient,
) -> None:
    token = register_and_login(
        client,
        email="teacher@example.com",
        role="instructor",
    )

    response = client.post(
        "/assignments",
        headers=auth_header(token),
        json={
            "title": "Invalid Policy",
            "description": "Weights do not total one hundred.",
            "grading_policy": {
                "io_weight": 70,
                "unit_weight": 20,
                "static_weight": 20,
            },
        },
    )

    assert response.status_code == 422
    assert "total 100" in response.json()["detail"]


def test_instructor_can_configure_assignment(
    client: TestClient,
) -> None:
    token = register_and_login(
        client,
        email="teacher@example.com",
        role="instructor",
    )
    assignment = create_assignment(client, token)

    configured = configure_complete_assignment(
        client,
        token,
        assignment["id"],
    )

    assert len(configured["io_test_cases"]) == 2
    assert configured["io_test_cases"][0]["visibility"] == "visible"
    assert configured["io_test_cases"][1]["visibility"] == "hidden"
    assert configured["unit_test_spec"]["test_code"] == (
        "assert solve(2, 3) == 5"
    )
    assert configured["static_analysis_rules"]["required_functions"] == [
        "solve"
    ]


def test_instructor_cannot_manage_another_instructors_assignment(
    client: TestClient,
) -> None:
    owner_token = register_and_login(
        client,
        email="owner@example.com",
        role="instructor",
    )
    assignment = create_assignment(client, owner_token)

    other_token = register_and_login(
        client,
        email="other@example.com",
        role="instructor",
    )

    response = client.get(
        f"/assignments/{assignment['id']}/manage",
        headers=auth_header(other_token),
    )

    assert response.status_code == 403


def test_publish_rejects_incomplete_default_assignment(
    client: TestClient,
) -> None:
    token = register_and_login(
        client,
        email="teacher@example.com",
        role="instructor",
    )
    assignment = create_assignment(client, token)

    response = client.post(
        f"/assignments/{assignment['id']}/publish",
        headers=auth_header(token),
    )

    assert response.status_code == 409
    assert "not ready to publish" in response.json()["detail"]


def test_instructor_can_publish_and_unpublish_complete_assignment(
    client: TestClient,
) -> None:
    token = register_and_login(
        client,
        email="teacher@example.com",
        role="instructor",
    )
    assignment = create_assignment(client, token)
    configure_complete_assignment(client, token, assignment["id"])

    published = publish_assignment(client, token, assignment["id"])
    assert published["status"] == "published"

    response = client.post(
        f"/assignments/{assignment['id']}/unpublish",
        headers=auth_header(token),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "draft"


def test_mine_lists_only_current_instructors_assignments(
    client: TestClient,
) -> None:
    first_token = register_and_login(
        client,
        email="first@example.com",
        role="instructor",
    )
    create_assignment(client, first_token, title="First Assignment")
    create_assignment(client, first_token, title="Second Assignment")

    second_token = register_and_login(
        client,
        email="second@example.com",
        role="instructor",
    )
    create_assignment(client, second_token, title="Other Assignment")

    response = client.get(
        "/assignments/mine",
        headers=auth_header(first_token),
    )

    assert response.status_code == 200
    assert [item["title"] for item in response.json()] == [
        "First Assignment",
        "Second Assignment",
    ]


def test_student_listing_contains_only_published_assignments(
    client: TestClient,
) -> None:
    instructor_token = register_and_login(
        client,
        email="teacher@example.com",
        role="instructor",
    )

    draft = create_assignment(
        client,
        instructor_token,
        title="Draft Assignment",
    )
    assert draft["status"] == "draft"

    published = create_assignment(
        client,
        instructor_token,
        title="Published Assignment",
    )
    configure_complete_assignment(
        client,
        instructor_token,
        published["id"],
    )
    publish_assignment(client, instructor_token, published["id"])

    student_token = register_and_login(
        client,
        email="student@example.com",
        role="student",
    )

    response = client.get(
        "/assignments",
        headers=auth_header(student_token),
    )

    assert response.status_code == 200
    assert [item["title"] for item in response.json()] == [
        "Published Assignment"
    ]


def test_student_detail_never_exposes_hidden_tests(
    client: TestClient,
) -> None:
    instructor_token = register_and_login(
        client,
        email="teacher@example.com",
        role="instructor",
    )
    assignment = create_assignment(client, instructor_token)
    configure_complete_assignment(
        client,
        instructor_token,
        assignment["id"],
    )
    publish_assignment(client, instructor_token, assignment["id"])

    student_token = register_and_login(
        client,
        email="student@example.com",
        role="student",
    )

    response = client.get(
        f"/assignments/{assignment['id']}",
        headers=auth_header(student_token),
    )

    assert response.status_code == 200
    payload = response.json()

    assert [test["name"] for test in payload["visible_io_examples"]] == [
        "visible example"
    ]
    assert payload["visible_unit_test"] is None
    serialized = response.text
    assert "hidden edge case" not in serialized
    assert "hidden unit tests" not in serialized
    assert "assert solve(2, 3) == 5" not in serialized


def test_student_cannot_access_draft_assignment(
    client: TestClient,
) -> None:
    instructor_token = register_and_login(
        client,
        email="teacher@example.com",
        role="instructor",
    )
    assignment = create_assignment(client, instructor_token)

    student_token = register_and_login(
        client,
        email="student@example.com",
        role="student",
    )

    response = client.get(
        f"/assignments/{assignment['id']}",
        headers=auth_header(student_token),
    )

    assert response.status_code == 404


def test_instructor_cannot_use_student_assignment_listing(
    client: TestClient,
) -> None:
    instructor_token = register_and_login(
        client,
        email="teacher@example.com",
        role="instructor",
    )

    response = client.get(
        "/assignments",
        headers=auth_header(instructor_token),
    )

    assert response.status_code == 403


def test_assignment_endpoints_require_authentication(
    client: TestClient,
) -> None:
    assert client.get("/assignments").status_code == 401
    assert client.get("/assignments/mine").status_code == 401
