from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from app.application.identity import (
    ExpiredTokenError,
    IdentityUser,
    InvalidTokenError,
    TokenClaims,
    TokenPair,
    TokenType,
)
from app.domain.identity import UserRole


class JwtTokenService:
    """JWT implementation of the application's token-service contract."""

    def __init__(
        self,
        *,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_ttl: timedelta = timedelta(minutes=30),
        refresh_token_ttl: timedelta = timedelta(days=7),
    ) -> None:
        if len(secret_key) < 32:
            raise ValueError("JWT secret key must contain at least 32 characters.")

        if access_token_ttl.total_seconds() <= 0:
            raise ValueError("Access-token lifetime must be positive.")

        if refresh_token_ttl.total_seconds() <= 0:
            raise ValueError("Refresh-token lifetime must be positive.")

        self._secret_key = secret_key
        self._algorithm = algorithm
        self._access_token_ttl = access_token_ttl
        self._refresh_token_ttl = refresh_token_ttl

    def issue_access(self, user: IdentityUser) -> str:
        return self._encode(
            user=user,
            token_type=TokenType.ACCESS,
            lifetime=self._access_token_ttl,
        )

    def issue_pair(self, user: IdentityUser) -> TokenPair:
        return TokenPair(
            access_token=self.issue_access(user),
            refresh_token=self._encode(
                user=user,
                token_type=TokenType.REFRESH,
                lifetime=self._refresh_token_ttl,
            ),
        )

    def decode(
        self,
        token: str,
        *,
        expected_type: TokenType,
    ) -> TokenClaims:
        try:
            payload: dict[str, Any] = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm],
                options={"require": ["sub", "role", "type", "iat", "exp"]},
            )
        except jwt.ExpiredSignatureError as exc:
            raise ExpiredTokenError("Token has expired.") from exc
        except jwt.InvalidTokenError as exc:
            raise InvalidTokenError("Token is invalid.") from exc

        try:
            token_type = TokenType(payload["type"])
            role = UserRole(payload["role"])
            subject = int(payload["sub"])
            issued_at = datetime.fromtimestamp(int(payload["iat"]), tz=timezone.utc)
            expires_at = datetime.fromtimestamp(int(payload["exp"]), tz=timezone.utc)
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidTokenError("Token contains invalid claims.") from exc

        if subject <= 0:
            raise InvalidTokenError("Token contains an invalid subject.")

        if token_type is not expected_type:
            article = "an" if expected_type is TokenType.ACCESS else "a"
            raise InvalidTokenError(
                f"Expected {article} {expected_type.value} token."
            )

        return TokenClaims(
            subject=subject,
            role=role,
            token_type=token_type,
            issued_at=issued_at,
            expires_at=expires_at,
        )

    def _encode(
        self,
        *,
        user: IdentityUser,
        token_type: TokenType,
        lifetime: timedelta,
    ) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user.id),
            "role": user.role.value,
            "type": token_type.value,
            "iat": now,
            "exp": now + lifetime,
        }

        return jwt.encode(
            payload,
            self._secret_key,
            algorithm=self._algorithm,
        )
