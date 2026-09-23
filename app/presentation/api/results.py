from __future__ import annotations

from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, HTTPException, status

from app.application.grading import (
    AIFeedbackGateway,
    AIFeedbackNotReadyError,
    AIFeedbackProtocolError,
    AIFeedbackUnavailableError,
    GenerateStudentAISuggestion,
    GetInstructorSubmissionResult,
    GetStudentSubmissionResult,
    GradingAssignmentNotFoundError,
    GradingResultMissingError,
    GradingSubmissionNotFoundError,
    ListInstructorAssignmentSubmissions,
    ResultAccessError,
)
from app.application.identity import IdentityUser
from app.domain.assessment import AssignmentOwnershipError
from app.infrastructure.persistence import SqlAlchemyGradingUnitOfWork

from .dependencies import (
    get_ai_feedback_gateway,
    get_grading_uow,
    require_instructor,
    require_student,
)
from .schemas.results import (
    AIFeedbackSuggestionResponse,
    InstructorSubmissionResultResponse,
    InstructorSubmissionSummaryResponse,
    StudentSubmissionResultResponse,
)

router = APIRouter(tags=["Results"])


def _raise_result_error(exc: Exception) -> NoReturn:
    if isinstance(
        exc,
        (
            GradingAssignmentNotFoundError,
            GradingSubmissionNotFoundError,
        ),
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    if isinstance(exc, (ResultAccessError, AssignmentOwnershipError)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    if isinstance(exc, AIFeedbackNotReadyError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    if isinstance(exc, AIFeedbackUnavailableError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    if isinstance(exc, AIFeedbackProtocolError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI feedback provider returned an invalid response.",
        ) from exc

    if isinstance(exc, GradingResultMissingError):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Completed grading result is unavailable.",
        ) from exc

    raise exc


@router.get(
    "/submissions/{submission_id}/result",
    response_model=StudentSubmissionResultResponse,
)
def get_student_result(
    submission_id: int,
    current_user: Annotated[
        IdentityUser,
        Depends(require_student),
    ],
    unit_of_work: Annotated[
        SqlAlchemyGradingUnitOfWork,
        Depends(get_grading_uow),
    ],
) -> StudentSubmissionResultResponse:
    try:
        view = GetStudentSubmissionResult(
            unit_of_work=unit_of_work
        ).execute(
            submission_id=submission_id,
            student_id=current_user.id,
        )
    except (
        GradingSubmissionNotFoundError,
        GradingResultMissingError,
        ResultAccessError,
    ) as exc:
        _raise_result_error(exc)

    return StudentSubmissionResultResponse.from_view(view)


@router.post(
    "/submissions/{submission_id}/ai-feedback",
    response_model=AIFeedbackSuggestionResponse,
)
def generate_student_ai_feedback(
    submission_id: int,
    current_user: Annotated[
        IdentityUser,
        Depends(require_student),
    ],
    unit_of_work: Annotated[
        SqlAlchemyGradingUnitOfWork,
        Depends(get_grading_uow),
    ],
    feedback_gateway: Annotated[
        AIFeedbackGateway,
        Depends(get_ai_feedback_gateway),
    ],
) -> AIFeedbackSuggestionResponse:
    try:
        suggestion = GenerateStudentAISuggestion(
            unit_of_work=unit_of_work,
            feedback_gateway=feedback_gateway,
        ).execute(
            submission_id=submission_id,
            student_id=current_user.id,
        )
    except (
        AIFeedbackNotReadyError,
        AIFeedbackProtocolError,
        AIFeedbackUnavailableError,
        GradingResultMissingError,
        GradingSubmissionNotFoundError,
        ResultAccessError,
    ) as exc:
        _raise_result_error(exc)

    return AIFeedbackSuggestionResponse.from_view(suggestion)


@router.get(
    "/assignments/{assignment_id}/submissions",
    response_model=list[InstructorSubmissionSummaryResponse],
)
def list_assignment_submissions(
    assignment_id: int,
    current_user: Annotated[
        IdentityUser,
        Depends(require_instructor),
    ],
    unit_of_work: Annotated[
        SqlAlchemyGradingUnitOfWork,
        Depends(get_grading_uow),
    ],
) -> list[InstructorSubmissionSummaryResponse]:
    try:
        views = ListInstructorAssignmentSubmissions(
            unit_of_work=unit_of_work
        ).execute(
            assignment_id=assignment_id,
            instructor_id=current_user.id,
        )
    except (
        GradingAssignmentNotFoundError,
        GradingResultMissingError,
        AssignmentOwnershipError,
    ) as exc:
        _raise_result_error(exc)

    return [
        InstructorSubmissionSummaryResponse.from_view(view)
        for view in views
    ]


@router.get(
    "/assignments/{assignment_id}/submissions/{submission_id}/result",
    response_model=InstructorSubmissionResultResponse,
)
def get_instructor_submission_result(
    assignment_id: int,
    submission_id: int,
    current_user: Annotated[
        IdentityUser,
        Depends(require_instructor),
    ],
    unit_of_work: Annotated[
        SqlAlchemyGradingUnitOfWork,
        Depends(get_grading_uow),
    ],
) -> InstructorSubmissionResultResponse:
    try:
        view = GetInstructorSubmissionResult(
            unit_of_work=unit_of_work
        ).execute(
            assignment_id=assignment_id,
            submission_id=submission_id,
            instructor_id=current_user.id,
        )
    except (
        GradingAssignmentNotFoundError,
        GradingSubmissionNotFoundError,
        GradingResultMissingError,
        AssignmentOwnershipError,
    ) as exc:
        _raise_result_error(exc)

    return InstructorSubmissionResultResponse.from_view(view)
