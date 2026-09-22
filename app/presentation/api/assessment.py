from __future__ import annotations

from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, HTTPException, status

from app.application.assessment import (
    AssignmentNotFoundError,
    ConfigureAssignment,
    ConfigureAssignmentCommand,
    CreateAssignment,
    CreateAssignmentCommand,
    GetInstructorAssignment,
    GetPublishedAssignment,
    ListInstructorAssignments,
    ListPublishedAssignments,
    PublishAssignment,
    PublishAssignmentCommand,
    PublishedAssignmentNotFoundError,
    UnpublishAssignment,
    UnpublishAssignmentCommand,
)
from app.application.identity import IdentityUser
from app.domain.assessment import (
    AssessmentValidationError,
    AssignmentNotReadyError,
    AssignmentOwnershipError,
)
from app.infrastructure.persistence import SqlAlchemyAssessmentUnitOfWork

from .dependencies import (
    get_assessment_uow,
    require_instructor,
    require_student,
)
from .schemas import (
    ConfigureAssignmentRequest,
    CreateAssignmentRequest,
    InstructorAssignmentResponse,
    PublishedAssignmentResponse,
)

router = APIRouter(prefix="/assignments", tags=["Assignments"])


def _raise_http_error(exc: Exception) -> NoReturn:
    if isinstance(
        exc,
        (AssignmentNotFoundError, PublishedAssignmentNotFoundError),
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    if isinstance(exc, AssignmentOwnershipError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    if isinstance(exc, AssignmentNotReadyError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    if isinstance(exc, AssessmentValidationError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    raise exc


@router.post(
    "",
    response_model=InstructorAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_assignment(
    payload: CreateAssignmentRequest,
    current_user: Annotated[
        IdentityUser,
        Depends(require_instructor),
    ],
    unit_of_work: Annotated[
        SqlAlchemyAssessmentUnitOfWork,
        Depends(get_assessment_uow),
    ],
) -> InstructorAssignmentResponse:
    use_case = CreateAssignment(unit_of_work=unit_of_work)

    try:
        result = use_case.execute(
            CreateAssignmentCommand(
                instructor_id=current_user.id,
                title=payload.title,
                description=payload.description,
                instructions=payload.instructions,
                grading_policy=(
                    payload.grading_policy.to_domain()
                    if payload.grading_policy is not None
                    else None
                ),
                execution_limits=(
                    payload.execution_limits.to_domain()
                    if payload.execution_limits is not None
                    else None
                ),
            )
        )
    except AssessmentValidationError as exc:
        _raise_http_error(exc)

    return InstructorAssignmentResponse.from_view(result)


@router.get(
    "/mine",
    response_model=list[InstructorAssignmentResponse],
)
def list_my_assignments(
    current_user: Annotated[
        IdentityUser,
        Depends(require_instructor),
    ],
    unit_of_work: Annotated[
        SqlAlchemyAssessmentUnitOfWork,
        Depends(get_assessment_uow),
    ],
) -> list[InstructorAssignmentResponse]:
    results = ListInstructorAssignments(
        unit_of_work=unit_of_work
    ).execute(instructor_id=current_user.id)

    return [
        InstructorAssignmentResponse.from_view(result)
        for result in results
    ]


@router.get(
    "/{assignment_id}/manage",
    response_model=InstructorAssignmentResponse,
)
def get_managed_assignment(
    assignment_id: int,
    current_user: Annotated[
        IdentityUser,
        Depends(require_instructor),
    ],
    unit_of_work: Annotated[
        SqlAlchemyAssessmentUnitOfWork,
        Depends(get_assessment_uow),
    ],
) -> InstructorAssignmentResponse:
    try:
        result = GetInstructorAssignment(
            unit_of_work=unit_of_work
        ).execute(
            assignment_id=assignment_id,
            instructor_id=current_user.id,
        )
    except (AssignmentNotFoundError, AssignmentOwnershipError) as exc:
        _raise_http_error(exc)

    return InstructorAssignmentResponse.from_view(result)


@router.patch(
    "/{assignment_id}/configuration",
    response_model=InstructorAssignmentResponse,
)
def configure_assignment(
    assignment_id: int,
    payload: ConfigureAssignmentRequest,
    current_user: Annotated[
        IdentityUser,
        Depends(require_instructor),
    ],
    unit_of_work: Annotated[
        SqlAlchemyAssessmentUnitOfWork,
        Depends(get_assessment_uow),
    ],
) -> InstructorAssignmentResponse:
    try:
        result = ConfigureAssignment(
            unit_of_work=unit_of_work
        ).execute(
            ConfigureAssignmentCommand(
                assignment_id=assignment_id,
                instructor_id=current_user.id,
                grading_policy=(
                    payload.grading_policy.to_domain()
                    if payload.grading_policy is not None
                    else None
                ),
                execution_limits=(
                    payload.execution_limits.to_domain()
                    if payload.execution_limits is not None
                    else None
                ),
                io_test_cases=tuple(
                    test.to_domain()
                    for test in payload.io_test_cases
                ),
                unit_test_spec=(
                    payload.unit_test_spec.to_domain()
                    if payload.unit_test_spec is not None
                    else None
                ),
                static_analysis_rules=(
                    payload.static_analysis_rules.to_domain()
                    if payload.static_analysis_rules is not None
                    else None
                ),
            )
        )
    except (
        AssignmentNotFoundError,
        AssignmentOwnershipError,
        AssignmentNotReadyError,
        AssessmentValidationError,
    ) as exc:
        _raise_http_error(exc)

    return InstructorAssignmentResponse.from_view(result)


@router.post(
    "/{assignment_id}/publish",
    response_model=InstructorAssignmentResponse,
)
def publish_assignment(
    assignment_id: int,
    current_user: Annotated[
        IdentityUser,
        Depends(require_instructor),
    ],
    unit_of_work: Annotated[
        SqlAlchemyAssessmentUnitOfWork,
        Depends(get_assessment_uow),
    ],
) -> InstructorAssignmentResponse:
    try:
        result = PublishAssignment(
            unit_of_work=unit_of_work
        ).execute(
            PublishAssignmentCommand(
                assignment_id=assignment_id,
                instructor_id=current_user.id,
            )
        )
    except (
        AssignmentNotFoundError,
        AssignmentOwnershipError,
        AssignmentNotReadyError,
    ) as exc:
        _raise_http_error(exc)

    return InstructorAssignmentResponse.from_view(result)


@router.post(
    "/{assignment_id}/unpublish",
    response_model=InstructorAssignmentResponse,
)
def unpublish_assignment(
    assignment_id: int,
    current_user: Annotated[
        IdentityUser,
        Depends(require_instructor),
    ],
    unit_of_work: Annotated[
        SqlAlchemyAssessmentUnitOfWork,
        Depends(get_assessment_uow),
    ],
) -> InstructorAssignmentResponse:
    try:
        result = UnpublishAssignment(
            unit_of_work=unit_of_work
        ).execute(
            UnpublishAssignmentCommand(
                assignment_id=assignment_id,
                instructor_id=current_user.id,
            )
        )
    except (AssignmentNotFoundError, AssignmentOwnershipError) as exc:
        _raise_http_error(exc)

    return InstructorAssignmentResponse.from_view(result)


@router.get(
    "",
    response_model=list[PublishedAssignmentResponse],
)
def list_published_assignments(
    current_user: Annotated[
        IdentityUser,
        Depends(require_student),
    ],
    unit_of_work: Annotated[
        SqlAlchemyAssessmentUnitOfWork,
        Depends(get_assessment_uow),
    ],
) -> list[PublishedAssignmentResponse]:
    _ = current_user
    results = ListPublishedAssignments(
        unit_of_work=unit_of_work
    ).execute()

    return [
        PublishedAssignmentResponse.from_view(result)
        for result in results
    ]


@router.get(
    "/{assignment_id}",
    response_model=PublishedAssignmentResponse,
)
def get_published_assignment(
    assignment_id: int,
    current_user: Annotated[
        IdentityUser,
        Depends(require_student),
    ],
    unit_of_work: Annotated[
        SqlAlchemyAssessmentUnitOfWork,
        Depends(get_assessment_uow),
    ],
) -> PublishedAssignmentResponse:
    _ = current_user

    try:
        result = GetPublishedAssignment(
            unit_of_work=unit_of_work
        ).execute(assignment_id=assignment_id)
    except PublishedAssignmentNotFoundError as exc:
        _raise_http_error(exc)

    return PublishedAssignmentResponse.from_view(result)
