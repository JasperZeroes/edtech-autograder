import pytest

from app.domain.identity import Email, IdentityValidationError, User, UserRole


def test_email_is_normalized() -> None:
    email = Email("  Student@Example.COM  ")

    assert email.value == "student@example.com"
    assert str(email) == "student@example.com"


@pytest.mark.parametrize(
    "raw_email",
    [
        "",
        "   ",
        "student",
        "student@",
        "@example.com",
        "student @example.com",
    ],
)
def test_invalid_email_is_rejected(raw_email: str) -> None:
    with pytest.raises(IdentityValidationError):
        Email(raw_email)


def test_register_student_creates_active_user_without_persistence_id() -> None:
    user = User.register(
        email=Email("student@example.com"),
        password_hash="hashed-password",
        role=UserRole.STUDENT,
        full_name=" Student One ",
    )

    assert user.id is None
    assert user.email == Email("student@example.com")
    assert user.role is UserRole.STUDENT
    assert user.full_name == "Student One"
    assert user.is_active is True
    assert user.is_student is True
    assert user.is_instructor is False


def test_register_instructor_sets_instructor_role() -> None:
    user = User.register(
        email=Email("teacher@example.com"),
        password_hash="hashed-password",
        role=UserRole.INSTRUCTOR,
    )

    assert user.is_instructor is True
    assert user.is_student is False


def test_blank_password_hash_is_rejected() -> None:
    with pytest.raises(IdentityValidationError):
        User.register(
            email=Email("student@example.com"),
            password_hash="   ",
            role=UserRole.STUDENT,
        )


def test_unsupported_role_is_rejected() -> None:
    with pytest.raises(IdentityValidationError):
        User(
            id=None,
            email=Email("user@example.com"),
            password_hash="hashed-password",
            role="admin",  # type: ignore[arg-type]
        )


def test_non_positive_persisted_user_id_is_rejected() -> None:
    with pytest.raises(IdentityValidationError):
        User(
            id=0,
            email=Email("user@example.com"),
            password_hash="hashed-password",
            role=UserRole.STUDENT,
        )


def test_user_can_be_deactivated_and_reactivated() -> None:
    user = User.register(
        email=Email("student@example.com"),
        password_hash="hashed-password",
        role=UserRole.STUDENT,
    )

    user.deactivate()
    assert user.is_active is False

    user.activate()
    assert user.is_active is True
