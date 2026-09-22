from __future__ import annotations

from collections.abc import Generator
from datetime import timedelta
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.identity import (
    ExpiredTokenError,
    IdentityUser,
    InvalidTokenError,
    TokenService,
    TokenType,
)
from app.config import get_auth_settings, get_database_settings
from app.domain.identity import UserRole
from app.infrastructure.persistence import (
    SqlAlchemyAssessmentUnitOfWork,
    SqlAlchemyIdentityUnitOfWork,
    SqlAlchemySubmissionUnitOfWork,
    create_database_engine,
    create_session_factory,
)
from app.infrastructure.queue import InMemoryGradingQueue
from app.infrastructure.security import Argon2PasswordHasher, JwtTokenService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


@lru_cache
def get_engine() -> Engine:
    settings = get_database_settings()
    return create_database_engine(settings.database_url)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return create_session_factory(get_engine())


def get_session() -> Generator[Session, None, None]:
    session_factory = get_session_factory()
    with session_factory() as session:
        yield session


def get_identity_uow(
    session: Annotated[Session, Depends(get_session)],
) -> SqlAlchemyIdentityUnitOfWork:
    return SqlAlchemyIdentityUnitOfWork(session)


def get_assessment_uow(
    session: Annotated[Session, Depends(get_session)],
) -> SqlAlchemyAssessmentUnitOfWork:
    return SqlAlchemyAssessmentUnitOfWork(session)


def get_submission_uow(
    session: Annotated[Session, Depends(get_session)],
) -> SqlAlchemySubmissionUnitOfWork:
    return SqlAlchemySubmissionUnitOfWork(session)


@lru_cache
def get_grading_queue() -> InMemoryGradingQueue:
    return InMemoryGradingQueue()


@lru_cache
def get_password_hasher() -> Argon2PasswordHasher:
    return Argon2PasswordHasher()


@lru_cache
def get_token_service() -> JwtTokenService:
    settings = get_auth_settings()
    return JwtTokenService(
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        access_token_ttl=timedelta(
            minutes=settings.jwt_access_token_minutes
        ),
        refresh_token_ttl=timedelta(
            days=settings.jwt_refresh_token_days
        ),
    )


def _credentials_exception(
    detail: str = "Could not validate credentials",
) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_identity(
    token: Annotated[str, Depends(oauth2_scheme)],
    unit_of_work: Annotated[
        SqlAlchemyIdentityUnitOfWork,
        Depends(get_identity_uow),
    ],
    token_service: Annotated[TokenService, Depends(get_token_service)],
) -> IdentityUser:
    try:
        claims = token_service.decode(
            token,
            expected_type=TokenType.ACCESS,
        )
    except (InvalidTokenError, ExpiredTokenError) as exc:
        raise _credentials_exception() from exc

    user = unit_of_work.users.get_by_id(claims.subject)
    if user is None:
        raise _credentials_exception()

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated.",
        )

    return IdentityUser.from_domain(user)


def require_role(*allowed_roles: UserRole):
    def role_dependency(
        current_user: Annotated[
            IdentityUser,
            Depends(get_current_identity),
        ],
    ) -> IdentityUser:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to perform this action.",
            )

        return current_user

    return role_dependency


require_student = require_role(UserRole.STUDENT)
require_instructor = require_role(UserRole.INSTRUCTOR)
