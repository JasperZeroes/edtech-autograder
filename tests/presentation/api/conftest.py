from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.infrastructure.security import JwtTokenService
from app.main import app
from app.presentation.api.dependencies import (
    get_assessment_uow,
    get_grading_queue,
    get_identity_uow,
    get_password_hasher,
    get_submission_uow,
    get_token_service,
)
from tests.application.assessment.fakes import FakeAssessmentUnitOfWork
from tests.application.identity.fakes import (
    FakeIdentityUnitOfWork,
    FakePasswordHasher,
)
from tests.application.submission.fakes import (
    FakeGradingQueue,
    FakeSubmissionUnitOfWork,
)

TEST_SECRET = "api-test-secret-key-with-at-least-32-characters"


@pytest.fixture
def unit_of_work() -> FakeIdentityUnitOfWork:
    return FakeIdentityUnitOfWork()


@pytest.fixture
def assessment_uow() -> FakeAssessmentUnitOfWork:
    return FakeAssessmentUnitOfWork()


@pytest.fixture
def submission_uow(
    assessment_uow: FakeAssessmentUnitOfWork,
) -> FakeSubmissionUnitOfWork:
    unit_of_work = FakeSubmissionUnitOfWork()
    unit_of_work.assignments = assessment_uow.assignments
    return unit_of_work


@pytest.fixture
def grading_queue() -> FakeGradingQueue:
    return FakeGradingQueue()


@pytest.fixture
def password_hasher() -> FakePasswordHasher:
    return FakePasswordHasher()


@pytest.fixture
def token_service() -> JwtTokenService:
    return JwtTokenService(secret_key=TEST_SECRET)


@pytest.fixture
def client(
    unit_of_work: FakeIdentityUnitOfWork,
    assessment_uow: FakeAssessmentUnitOfWork,
    submission_uow: FakeSubmissionUnitOfWork,
    grading_queue: FakeGradingQueue,
    password_hasher: FakePasswordHasher,
    token_service: JwtTokenService,
) -> TestClient:
    app.dependency_overrides[get_identity_uow] = lambda: unit_of_work
    app.dependency_overrides[get_assessment_uow] = lambda: assessment_uow
    app.dependency_overrides[get_submission_uow] = lambda: submission_uow
    app.dependency_overrides[get_grading_queue] = lambda: grading_queue
    app.dependency_overrides[get_password_hasher] = lambda: password_hasher
    app.dependency_overrides[get_token_service] = lambda: token_service

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
