import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.domain.identity import Email, User, UserRole
from app.infrastructure.persistence.base import Base
from app.infrastructure.persistence.repositories import SqlAlchemyUserRepository
from app.infrastructure.persistence.repositories.user_repository import (
    UserPersistenceError,
)


@pytest.fixture
def session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine, expire_on_commit=False) as db_session:
        yield db_session

    Base.metadata.drop_all(engine)
    engine.dispose()


def test_save_new_user_assigns_persistence_id(session: Session) -> None:
    repository = SqlAlchemyUserRepository(session)
    user = User.register(
        email=Email("student@example.com"),
        password_hash="hashed-password",
        role=UserRole.STUDENT,
        full_name="Student One",
    )

    saved = repository.save(user)

    assert saved is user
    assert user.id is not None
    assert user.id > 0


def test_get_by_email_rehydrates_domain_user(session: Session) -> None:
    repository = SqlAlchemyUserRepository(session)
    repository.save(
        User.register(
            email=Email("Teacher@Example.com"),
            password_hash="hashed-password",
            role=UserRole.INSTRUCTOR,
            full_name="Teacher One",
        )
    )

    loaded = repository.get_by_email(Email("teacher@example.com"))

    assert loaded is not None
    assert loaded.email == Email("teacher@example.com")
    assert loaded.role is UserRole.INSTRUCTOR
    assert loaded.full_name == "Teacher One"
    assert loaded.is_active is True


def test_get_by_id_returns_persisted_user(session: Session) -> None:
    repository = SqlAlchemyUserRepository(session)
    user = User.register(
        email=Email("student@example.com"),
        password_hash="hashed-password",
        role=UserRole.STUDENT,
    )
    repository.save(user)

    loaded = repository.get_by_id(user.id)  # type: ignore[arg-type]

    assert loaded is not None
    assert loaded.id == user.id
    assert loaded.email == user.email


def test_missing_user_returns_none(session: Session) -> None:
    repository = SqlAlchemyUserRepository(session)

    assert repository.get_by_id(999) is None
    assert repository.get_by_email(Email("missing@example.com")) is None


def test_save_updates_existing_user_state(session: Session) -> None:
    repository = SqlAlchemyUserRepository(session)
    user = User.register(
        email=Email("student@example.com"),
        password_hash="hashed-password",
        role=UserRole.STUDENT,
    )
    repository.save(user)

    user.deactivate()
    repository.save(user)
    session.expire_all()

    loaded = repository.get_by_id(user.id)  # type: ignore[arg-type]

    assert loaded is not None
    assert loaded.is_active is False


def test_save_rejects_update_for_missing_persistence_record(
    session: Session,
) -> None:
    repository = SqlAlchemyUserRepository(session)
    user = User(
        id=999,
        email=Email("ghost@example.com"),
        password_hash="hashed-password",
        role=UserRole.STUDENT,
    )

    with pytest.raises(UserPersistenceError):
        repository.save(user)
