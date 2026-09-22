class SubmissionApplicationError(Exception):
    """Base class for submission application-layer failures."""


class AssignmentUnavailableError(SubmissionApplicationError):
    """Raised when a student cannot submit to the requested assignment."""


class SubmissionNotFoundError(SubmissionApplicationError):
    """Raised when a requested submission does not exist."""


class SubmissionAccessError(SubmissionApplicationError):
    """Raised when a student attempts to access another student's submission."""
