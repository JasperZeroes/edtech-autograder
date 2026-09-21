import pytest

from app.application.identity import (
    DuplicateEmailError,
    InvalidPasswordError,
    RegisterUser,
    RegisterUserCommand,
)
from app.domain.identity import Email, User, UserRole

from .fakes import FakeIdentityUnitOfWork, FakePasswordHasher


def test_register_user_hashes_password_and_commits() -> None:
    unit_of_work = FakeIdentityUnitOfWork()
    password_hasher = FakePasswordHasher()
    use_case = RegisterUser(
        unit_of_work=unit_of_work,
        password_hasher=password_hasher,
    )

    result = use_case.execute(
        RegisterUserCommand(
            email=" Student@Example.COM ",
            password="password123",
            role=UserRole.STUDENT,
            full_name=" Student One ",
        )
    )

    persisted = unit_of_work.users.get_by_id(result.id)

    assert result.email == "student@example.com"
    assert result.role is UserRole.STUDENT
    assert result.full_name == "Student One"
    assert result.is_active is True
    assert persisted is not None
    assert persisted.password_hash == "hashed::password123"
    assert password_hasher.hashed_passwords == ["password123"]
    assert unit_of_work.committed is True
    assert unit_of_work.rolled_back is False


def test_register_user_rejects_duplicate_email_before_hashing() -> None:
    existing = User(
        id=1,
        email=Email("student@example.com"),
        password_hash="hashed::existing-password",
        role=UserRole.STUDENT,
    )
    unit_of_work = FakeIdentityUnitOfWork([existing])
    password_hasher = FakePasswordHasher()
    use_case = RegisterUser(
        unit_of_work=unit_of_work,
        password_hasher=password_hasher,
    )

    with pytest.raises(DuplicateEmailError):
        use_case.execute(
            RegisterUserCommand(
                email="STUDENT@example.com",
                password="different-password",
                role=UserRole.STUDENT,
            )
        )

    assert password_hasher.hashed_passwords == []
    assert unit_of_work.committed is False


@pytest.mark.parametrize(
    "password",
    [
        "",
        "short",
        "x" * 129,
    ],
)
def test_register_user_rejects_password_outside_supported_length(
    password: str,
) -> None:
    unit_of_work = FakeIdentityUnitOfWork()
    use_case = RegisterUser(
        unit_of_work=unit_of_work,
        password_hasher=FakePasswordHasher(),
    )

    with pytest.raises(InvalidPasswordError):
        use_case.execute(
            RegisterUserCommand(
                email="student@example.com",
                password=password,
                role=UserRole.STUDENT,
            )
        )

    assert unit_of_work.committed is False


def test_registration_result_does_not_expose_password_hash() -> None:
    use_case = RegisterUser(
        unit_of_work=FakeIdentityUnitOfWork(),
        password_hasher=FakePasswordHasher(),
    )

    result = use_case.execute(
        RegisterUserCommand(
            email="teacher@example.com",
            password="password123",
            role=UserRole.INSTRUCTOR,
        )
    )

    assert not hasattr(result, "password_hash")
    assert not hasattr(result, "password")


def test_registration_rolls_back_when_repository_save_fails() -> None:
    unit_of_work = FakeIdentityUnitOfWork()

    def failing_save(user: User) -> User:
        raise RuntimeError("persistence failed")

    unit_of_work.users.save = failing_save  # type: ignore[method-assign]

    use_case = RegisterUser(
        unit_of_work=unit_of_work,
        password_hasher=FakePasswordHasher(),
    )

    with pytest.raises(RuntimeError, match="persistence failed"):
        use_case.execute(
            RegisterUserCommand(
                email="student@example.com",
                password="password123",
                role=UserRole.STUDENT,
            )
        )

    assert unit_of_work.committed is False
    assert unit_of_work.rolled_back is True
