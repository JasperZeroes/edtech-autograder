import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.domain.identity import Email, User, UserRole
from app.infrastructure.persistence import Base, SqlAlchemyIdentityUnitOfWork
from app.infrastructure.persistence.models import UserModel


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


def make_user(email: str = "student@example.com") -> User:
    return User.register(
        email=Email(email),
        password_hash="$argon2id$test-hash",
        role=UserRole.STUDENT,
    )


def test_unit_of_work_exposes_user_repository(session: Session) -> None:
    unit_of_work = SqlAlchemyIdentityUnitOfWork(session)

    user = unit_of_work.users.save(make_user())

    assert user.id is not None


def test_commit_persists_flushed_repository_changes(session: Session) -> None:
    unit_of_work = SqlAlchemyIdentityUnitOfWork(session)
    user = unit_of_work.users.save(make_user())

    unit_of_work.commit()
    user_id = user.id

    session.expire_all()
    persisted = session.get(UserModel, user_id)

    assert persisted is not None
    assert persisted.email == "student@example.com"


def test_rollback_discards_flushed_new_user(session: Session) -> None:
    unit_of_work = SqlAlchemyIdentityUnitOfWork(session)
    user = unit_of_work.users.save(make_user())

    assert user.id is not None

    unit_of_work.rollback()

    persisted = session.get(UserModel, user.id)

    assert persisted is None
