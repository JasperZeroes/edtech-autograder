import pytest

from app.application.identity import (
    AuthenticateUser,
    AuthenticateUserCommand,
    InactiveUserError,
    InvalidCredentialsError,
)
from app.domain.identity import Email, User, UserRole

from .fakes import FakeIdentityUnitOfWork, FakePasswordHasher


def make_user(*, active: bool = True) -> User:
    return User(
        id=1,
        email=Email("student@example.com"),
        password_hash="hashed::correct-password",
        role=UserRole.STUDENT,
        full_name="Student One",
        is_active=active,
    )


def test_authenticate_user_returns_safe_identity_for_valid_credentials() -> None:
    unit_of_work = FakeIdentityUnitOfWork([make_user()])
    password_hasher = FakePasswordHasher()
    use_case = AuthenticateUser(
        unit_of_work=unit_of_work,
        password_hasher=password_hasher,
    )

    result = use_case.execute(
        AuthenticateUserCommand(
            email="STUDENT@example.com",
            password="correct-password",
        )
    )

    assert result.id == 1
    assert result.email == "student@example.com"
    assert result.role is UserRole.STUDENT
    assert result.full_name == "Student One"
    assert result.is_active is True
    assert not hasattr(result, "password_hash")
    assert password_hasher.verified_passwords == [
        ("correct-password", "hashed::correct-password")
    ]


def test_unknown_email_raises_generic_invalid_credentials() -> None:
    use_case = AuthenticateUser(
        unit_of_work=FakeIdentityUnitOfWork(),
        password_hasher=FakePasswordHasher(),
    )

    with pytest.raises(
        InvalidCredentialsError,
        match="Invalid email or password",
    ):
        use_case.execute(
            AuthenticateUserCommand(
                email="missing@example.com",
                password="anything123",
            )
        )


def test_wrong_password_raises_same_generic_invalid_credentials() -> None:
    use_case = AuthenticateUser(
        unit_of_work=FakeIdentityUnitOfWork([make_user()]),
        password_hasher=FakePasswordHasher(),
    )

    with pytest.raises(
        InvalidCredentialsError,
        match="Invalid email or password",
    ):
        use_case.execute(
            AuthenticateUserCommand(
                email="student@example.com",
                password="wrong-password",
            )
        )


def test_deactivated_user_cannot_authenticate() -> None:
    use_case = AuthenticateUser(
        unit_of_work=FakeIdentityUnitOfWork([make_user(active=False)]),
        password_hasher=FakePasswordHasher(),
    )

    with pytest.raises(InactiveUserError, match="Account is deactivated"):
        use_case.execute(
            AuthenticateUserCommand(
                email="student@example.com",
                password="correct-password",
            )
        )


def test_authentication_does_not_commit_transaction() -> None:
    unit_of_work = FakeIdentityUnitOfWork([make_user()])
    use_case = AuthenticateUser(
        unit_of_work=unit_of_work,
        password_hasher=FakePasswordHasher(),
    )

    use_case.execute(
        AuthenticateUserCommand(
            email="student@example.com",
            password="correct-password",
        )
    )

    assert unit_of_work.committed is False
    assert unit_of_work.rolled_back is False
