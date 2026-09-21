from __future__ import annotations

from fastapi.testclient import TestClient

from app.application.identity import TokenType
from app.domain.identity import Email
from app.infrastructure.security import JwtTokenService
from tests.application.identity.fakes import FakeIdentityUnitOfWork


def register_student(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/auth/register",
        json={
            "email": "Student@Example.COM",
            "password": "password123",
            "role": "student",
            "full_name": " Student One ",
        },
    )

    assert response.status_code == 201
    return response.json()


def login_student(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/auth/login",
        data={
            "username": "student@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 200
    return response.json()


def test_register_returns_safe_normalized_user(client: TestClient) -> None:
    payload = register_student(client)

    assert payload == {
        "id": 1,
        "email": "student@example.com",
        "role": "student",
        "full_name": "Student One",
        "is_active": True,
    }
    assert "password" not in payload
    assert "password_hash" not in payload


def test_register_rejects_duplicate_email_case_insensitively(
    client: TestClient,
) -> None:
    register_student(client)

    response = client.post(
        "/auth/register",
        json={
            "email": "STUDENT@example.com",
            "password": "another-password",
            "role": "student",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "A user with this email address already exists."
    )


def test_register_rejects_invalid_email(client: TestClient) -> None:
    response = client.post(
        "/auth/register",
        json={
            "email": "not-an-email",
            "password": "password123",
            "role": "student",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "A valid email address is required."


def test_register_request_rejects_short_password(client: TestClient) -> None:
    response = client.post(
        "/auth/register",
        json={
            "email": "student@example.com",
            "password": "short",
            "role": "student",
        },
    )

    assert response.status_code == 422


def test_login_returns_access_and_refresh_tokens(
    client: TestClient,
    token_service: JwtTokenService,
) -> None:
    register_student(client)

    payload = login_student(client)

    assert payload["token_type"] == "bearer"
    assert payload["access_token"]
    assert payload["refresh_token"]

    access_claims = token_service.decode(
        payload["access_token"],
        expected_type=TokenType.ACCESS,
    )
    refresh_claims = token_service.decode(
        payload["refresh_token"],
        expected_type=TokenType.REFRESH,
    )

    assert access_claims.subject == 1
    assert refresh_claims.subject == 1


def test_login_rejects_invalid_credentials(client: TestClient) -> None:
    register_student(client)

    response = client.post(
        "/auth/login",
        data={
            "username": "student@example.com",
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."
    assert response.headers["www-authenticate"] == "Bearer"


def test_login_rejects_inactive_user(
    client: TestClient,
    unit_of_work: FakeIdentityUnitOfWork,
) -> None:
    register_student(client)
    user = unit_of_work.users.get_by_email(Email("student@example.com"))
    assert user is not None
    user.deactivate()

    response = client.post(
        "/auth/login",
        data={
            "username": "student@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Account is deactivated."


def test_refresh_exchanges_refresh_token_for_new_access_token(
    client: TestClient,
    token_service: JwtTokenService,
) -> None:
    register_student(client)
    tokens = login_student(client)

    response = client.post(
        "/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["access_token"]

    claims = token_service.decode(
        payload["access_token"],
        expected_type=TokenType.ACCESS,
    )
    assert claims.subject == 1


def test_refresh_rejects_access_token(client: TestClient) -> None:
    register_student(client)
    tokens = login_student(client)

    response = client.post(
        "/auth/refresh",
        json={"refresh_token": tokens["access_token"]},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired refresh token."


def test_refresh_rejects_deactivated_user(
    client: TestClient,
    unit_of_work: FakeIdentityUnitOfWork,
) -> None:
    register_student(client)
    tokens = login_student(client)

    user = unit_of_work.users.get_by_email(Email("student@example.com"))
    assert user is not None
    user.deactivate()

    response = client.post(
        "/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )

    assert response.status_code == 401


def test_me_returns_current_user(client: TestClient) -> None:
    register_student(client)
    tokens = login_student(client)

    response = client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {tokens['access_token']}",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "email": "student@example.com",
        "role": "student",
        "full_name": "Student One",
        "is_active": True,
    }


def test_me_requires_bearer_token(client: TestClient) -> None:
    response = client.get("/auth/me")

    assert response.status_code == 401


def test_me_rejects_refresh_token(client: TestClient) -> None:
    register_student(client)
    tokens = login_student(client)

    response = client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {tokens['refresh_token']}",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"


def test_me_rechecks_account_active_state(
    client: TestClient,
    unit_of_work: FakeIdentityUnitOfWork,
) -> None:
    register_student(client)
    tokens = login_student(client)

    user = unit_of_work.users.get_by_email(Email("student@example.com"))
    assert user is not None
    user.deactivate()

    response = client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {tokens['access_token']}",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Account is deactivated."


def test_health_endpoint_remains_available(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
