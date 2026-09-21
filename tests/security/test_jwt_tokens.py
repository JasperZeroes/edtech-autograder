from datetime import timedelta

import jwt
import pytest

from app.application.identity import (
    ExpiredTokenError,
    IdentityUser,
    InvalidTokenError,
    TokenType,
)
from app.domain.identity import UserRole
from app.infrastructure.security import JwtTokenService

SECRET = "test-secret-key-with-at-least-32-characters"


@pytest.fixture
def user() -> IdentityUser:
    return IdentityUser(
        id=42,
        email="student@example.com",
        role=UserRole.STUDENT,
        full_name="Student One",
        is_active=True,
    )


@pytest.fixture
def service() -> JwtTokenService:
    return JwtTokenService(secret_key=SECRET)


def test_issue_pair_creates_access_and_refresh_tokens(
    service: JwtTokenService,
    user: IdentityUser,
) -> None:
    pair = service.issue_pair(user)

    access_claims = service.decode(
        pair.access_token,
        expected_type=TokenType.ACCESS,
    )
    refresh_claims = service.decode(
        pair.refresh_token,
        expected_type=TokenType.REFRESH,
    )

    assert access_claims.subject == 42
    assert access_claims.role is UserRole.STUDENT
    assert access_claims.token_type is TokenType.ACCESS
    assert refresh_claims.subject == 42
    assert refresh_claims.token_type is TokenType.REFRESH
    assert refresh_claims.expires_at > access_claims.expires_at


def test_refresh_token_cannot_be_used_as_access_token(
    service: JwtTokenService,
    user: IdentityUser,
) -> None:
    pair = service.issue_pair(user)

    with pytest.raises(InvalidTokenError, match="Expected an access token"):
        service.decode(pair.refresh_token, expected_type=TokenType.ACCESS)


def test_access_token_cannot_be_used_as_refresh_token(
    service: JwtTokenService,
    user: IdentityUser,
) -> None:
    pair = service.issue_pair(user)

    with pytest.raises(InvalidTokenError, match="Expected a refresh token"):
        service.decode(pair.access_token, expected_type=TokenType.REFRESH)


def test_tampered_token_is_rejected(
    service: JwtTokenService,
    user: IdentityUser,
) -> None:
    token = service.issue_pair(user).access_token
    tampered = token[:-1] + ("a" if token[-1] != "a" else "b")

    with pytest.raises(InvalidTokenError):
        service.decode(tampered, expected_type=TokenType.ACCESS)


def test_token_signed_with_different_secret_is_rejected(
    service: JwtTokenService,
) -> None:
    token = jwt.encode(
        {
            "sub": "42",
            "role": "student",
            "type": "access",
            "iat": 1_700_000_000,
            "exp": 4_000_000_000,
        },
        "different-secret-key-that-is-long-enough",
        algorithm="HS256",
    )

    with pytest.raises(InvalidTokenError):
        service.decode(token, expected_type=TokenType.ACCESS)


def test_expired_token_is_rejected() -> None:
    service = JwtTokenService(secret_key=SECRET)
    expired = jwt.encode(
        {
            "sub": "42",
            "role": "student",
            "type": "access",
            "iat": 1_600_000_000,
            "exp": 1_600_000_001,
        },
        SECRET,
        algorithm="HS256",
    )

    with pytest.raises(ExpiredTokenError):
        service.decode(expired, expected_type=TokenType.ACCESS)


def test_invalid_role_claim_is_rejected() -> None:
    service = JwtTokenService(secret_key=SECRET)
    token = jwt.encode(
        {
            "sub": "42",
            "role": "admin",
            "type": "access",
            "iat": 1_700_000_000,
            "exp": 4_000_000_000,
        },
        SECRET,
        algorithm="HS256",
    )

    with pytest.raises(InvalidTokenError, match="invalid claims"):
        service.decode(token, expected_type=TokenType.ACCESS)


def test_secret_key_must_be_at_least_32_characters() -> None:
    with pytest.raises(ValueError, match="at least 32"):
        JwtTokenService(secret_key="too-short")


def test_token_lifetimes_must_be_positive() -> None:
    with pytest.raises(ValueError, match="Access-token lifetime"):
        JwtTokenService(
            secret_key=SECRET,
            access_token_ttl=timedelta(seconds=0),
        )

    with pytest.raises(ValueError, match="Refresh-token lifetime"):
        JwtTokenService(
            secret_key=SECRET,
            refresh_token_ttl=timedelta(seconds=0),
        )


def test_issue_access_creates_access_token(
    service: JwtTokenService,
    user: IdentityUser,
) -> None:
    token = service.issue_access(user)

    claims = service.decode(token, expected_type=TokenType.ACCESS)

    assert claims.subject == 42
    assert claims.token_type is TokenType.ACCESS
