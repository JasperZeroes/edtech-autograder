class SubmissionApplicationError(Exception):
    """Base class for submission application-layer failures."""


class AssignmentUnavailableError(SubmissionApplicationError):
    """Raised when a student cannot submit to the requested assignment."""


class SubmissionNotFoundError(SubmissionApplicationError):
    """Raised when a requested submission does not exist."""


class SubmissionAccessError(SubmissionApplicationError):
    """Raised when a student attempts to access another student's submission."""


class SubmissionQueueError(SubmissionApplicationError):
    """Raised after persistence when grading dispatch fails."""

    def __init__(self, submission_id: int) -> None:
        self.submission_id = submission_id
        super().__init__(
            f"Submission {submission_id} was saved but could not be "
            "queued for grading."
        )
