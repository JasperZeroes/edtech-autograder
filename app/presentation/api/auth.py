from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.application.identity import (
    AuthenticateUser,
    AuthenticateUserCommand,
    DuplicateEmailError,
    ExpiredTokenError,
    IdentityUser,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidPasswordError,
    InvalidTokenError,
    PasswordHasher,
    RegisterUser,
    RegisterUserCommand,
    TokenService,
    TokenType,
)
from app.domain.identity import IdentityValidationError
from app.infrastructure.persistence import SqlAlchemyIdentityUnitOfWork

from .dependencies import (
    get_current_identity,
    get_identity_uow,
    get_password_hasher,
    get_token_service,
)
from .schemas import (
    AccessTokenResponse,
    TokenRefreshRequest,
    TokenResponse,
    UserRegisterRequest,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    payload: UserRegisterRequest,
    unit_of_work: Annotated[
        SqlAlchemyIdentityUnitOfWork,
        Depends(get_identity_uow),
    ],
    password_hasher: Annotated[
        PasswordHasher,
        Depends(get_password_hasher),
    ],
) -> UserResponse:
    use_case = RegisterUser(
        unit_of_work=unit_of_work,
        password_hasher=password_hasher,
    )

    try:
        user = use_case.execute(
            RegisterUserCommand(
                email=payload.email,
                password=payload.password,
                role=payload.role,
                full_name=payload.full_name,
            )
        )
    except DuplicateEmailError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except (InvalidPasswordError, IdentityValidationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return UserResponse.from_identity(user)


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    unit_of_work: Annotated[
        SqlAlchemyIdentityUnitOfWork,
        Depends(get_identity_uow),
    ],
    password_hasher: Annotated[
        PasswordHasher,
        Depends(get_password_hasher),
    ],
    token_service: Annotated[
        TokenService,
        Depends(get_token_service),
    ],
) -> TokenResponse:
    use_case = AuthenticateUser(
        unit_of_work=unit_of_work,
        password_hasher=password_hasher,
    )

    try:
        user = use_case.execute(
            AuthenticateUserCommand(
                email=form_data.username,
                password=form_data.password,
            )
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except InactiveUserError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    return TokenResponse.from_pair(token_service.issue_pair(user))


@router.post(
    "/refresh",
    response_model=AccessTokenResponse,
)
def refresh(
    payload: TokenRefreshRequest,
    unit_of_work: Annotated[
        SqlAlchemyIdentityUnitOfWork,
        Depends(get_identity_uow),
    ],
    token_service: Annotated[
        TokenService,
        Depends(get_token_service),
    ],
) -> AccessTokenResponse:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        claims = token_service.decode(
            payload.refresh_token,
            expected_type=TokenType.REFRESH,
        )
    except (InvalidTokenError, ExpiredTokenError) as exc:
        raise credentials_exception from exc

    user = unit_of_work.users.get_by_id(claims.subject)
    if user is None or not user.is_active:
        raise credentials_exception

    identity = IdentityUser.from_domain(user)

    return AccessTokenResponse(
        access_token=token_service.issue_access(identity)
    )


@router.get(
    "/me",
    response_model=UserResponse,
)
def me(
    current_user: Annotated[
        IdentityUser,
        Depends(get_current_identity),
    ],
) -> UserResponse:
    return UserResponse.from_identity(current_user)
