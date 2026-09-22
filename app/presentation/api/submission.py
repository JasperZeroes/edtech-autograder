from __future__ import annotations

from typing import Annotated, NoReturn

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)

from app.application.identity import IdentityUser
from app.application.submission import (
    AssignmentUnavailableError,
    CreateSubmissionCommand,
    GetStudentSubmission,
    GradingQueue,
    ListStudentSubmissions,
    SubmissionAccessError,
    SubmissionNotFoundError,
    SubmissionQueueError,
    SubmitForGrading,
)
from app.domain.submission import SubmissionValidationError
from app.infrastructure.persistence import SqlAlchemySubmissionUnitOfWork

from .dependencies import (
    get_grading_queue,
    get_submission_uow,
    require_student,
)
from .schemas import (
    SubmissionDetailResponse,
    SubmissionSummaryResponse,
)

router = APIRouter(tags=["Submissions"])

MAX_SOURCE_FILE_BYTES = 256 * 1024
_ALLOWED_SOURCE_CONTENT_TYPES = {
    "application/octet-stream",
    "text/plain",
    "text/x-python",
    "text/x-script.python",
}


def _raise_submission_error(exc: Exception) -> NoReturn:
    if isinstance(exc, AssignmentUnavailableError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    if isinstance(exc, SubmissionNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    if isinstance(exc, SubmissionAccessError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    if isinstance(exc, SubmissionQueueError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
            headers={"Retry-After": "5"},
        ) from exc

    if isinstance(exc, SubmissionValidationError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    raise exc


async def _read_python_source(file: UploadFile) -> str:
    filename = file.filename or ""
    if not filename.lower().endswith(".py"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only .py source files are accepted.",
        )

    if (
        file.content_type
        and file.content_type not in _ALLOWED_SOURCE_CONTENT_TYPES
    ):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Uploaded file does not have a supported Python "
            "source content type.",
        )

    payload = await file.read(MAX_SOURCE_FILE_BYTES + 1)

    if len(payload) > MAX_SOURCE_FILE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Python source file must not exceed 256 KiB.",
        )

    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Python source file must be valid UTF-8 text.",
        ) from exc


@router.post(
    "/assignments/{assignment_id}/submissions",
    response_model=SubmissionDetailResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def submit_assignment(
    assignment_id: int,
    file: Annotated[UploadFile, File(...)],
    current_user: Annotated[
        IdentityUser,
        Depends(require_student),
    ],
    unit_of_work: Annotated[
        SqlAlchemySubmissionUnitOfWork,
        Depends(get_submission_uow),
    ],
    grading_queue: Annotated[
        GradingQueue,
        Depends(get_grading_queue),
    ],
) -> SubmissionDetailResponse:
    source_code = await _read_python_source(file)

    try:
        result = SubmitForGrading(
            unit_of_work=unit_of_work,
            grading_queue=grading_queue,
        ).execute(
            CreateSubmissionCommand(
                assignment_id=assignment_id,
                student_id=current_user.id,
                source_code=source_code,
            )
        )
    except (
        AssignmentUnavailableError,
        SubmissionQueueError,
        SubmissionValidationError,
    ) as exc:
        _raise_submission_error(exc)

    return SubmissionDetailResponse.from_view(result)


@router.get(
    "/submissions/mine",
    response_model=list[SubmissionSummaryResponse],
)
def list_my_submissions(
    current_user: Annotated[
        IdentityUser,
        Depends(require_student),
    ],
    unit_of_work: Annotated[
        SqlAlchemySubmissionUnitOfWork,
        Depends(get_submission_uow),
    ],
) -> list[SubmissionSummaryResponse]:
    results = ListStudentSubmissions(
        unit_of_work=unit_of_work
    ).execute(student_id=current_user.id)

    return [
        SubmissionSummaryResponse.from_view(result)
        for result in results
    ]


@router.get(
    "/submissions/{submission_id}",
    response_model=SubmissionDetailResponse,
)
def get_my_submission(
    submission_id: int,
    current_user: Annotated[
        IdentityUser,
        Depends(require_student),
    ],
    unit_of_work: Annotated[
        SqlAlchemySubmissionUnitOfWork,
        Depends(get_submission_uow),
    ],
) -> SubmissionDetailResponse:
    try:
        result = GetStudentSubmission(
            unit_of_work=unit_of_work
        ).execute(
            submission_id=submission_id,
            student_id=current_user.id,
        )
    except (SubmissionNotFoundError, SubmissionAccessError) as exc:
        _raise_submission_error(exc)

    return SubmissionDetailResponse.from_view(result)
