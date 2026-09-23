from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.domain.grading import GradingResult, StoredGradingResult
from app.infrastructure.security import JwtTokenService
from app.main import app
from app.presentation.api.dependencies import (
    get_assessment_uow,
    get_grading_queue,
    get_grading_uow,
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

TEST_SECRET = "system-test-secret-key-with-at-least-32-characters"


class SystemGradingResultRepository:
    def __init__(self) -> None:
        self._results: dict[int, StoredGradingResult] = {}
        self._next_id = 1

    def get_by_submission_id(
        self,
        submission_id: int,
    ) -> StoredGradingResult | None:
        return self._results.get(submission_id)

    def save(
        self,
        *,
        submission_id: int,
        result: GradingResult,
    ) -> StoredGradingResult:
        stored = StoredGradingResult(
            id=self._next_id,
            submission_id=submission_id,
            result=result,
        )
        self._next_id += 1
        self._results[submission_id] = stored
        return stored


class SystemGradingUnitOfWork:
    def __init__(
        self,
        *,
        assessment_uow: FakeAssessmentUnitOfWork,
        submission_uow: FakeSubmissionUnitOfWork,
    ) -> None:
        self.assignments = assessment_uow.assignments
        self.submissions = submission_uow.submissions
        self.grading_results = SystemGradingResultRepository()
        self.commits = 0
        self.rollbacks = 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


@pytest.fixture
def identity_uow() -> FakeIdentityUnitOfWork:
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
def grading_uow(
    assessment_uow: FakeAssessmentUnitOfWork,
    submission_uow: FakeSubmissionUnitOfWork,
) -> SystemGradingUnitOfWork:
    return SystemGradingUnitOfWork(
        assessment_uow=assessment_uow,
        submission_uow=submission_uow,
    )


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
    identity_uow: FakeIdentityUnitOfWork,
    assessment_uow: FakeAssessmentUnitOfWork,
    submission_uow: FakeSubmissionUnitOfWork,
    grading_uow: SystemGradingUnitOfWork,
    grading_queue: FakeGradingQueue,
    password_hasher: FakePasswordHasher,
    token_service: JwtTokenService,
) -> TestClient:
    app.dependency_overrides[get_identity_uow] = lambda: identity_uow
    app.dependency_overrides[get_assessment_uow] = lambda: assessment_uow
    app.dependency_overrides[get_submission_uow] = lambda: submission_uow
    app.dependency_overrides[get_grading_uow] = lambda: grading_uow
    app.dependency_overrides[get_grading_queue] = lambda: grading_queue
    app.dependency_overrides[get_password_hasher] = lambda: password_hasher
    app.dependency_overrides[get_token_service] = lambda: token_service

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
