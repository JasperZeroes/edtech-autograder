class AssessmentApplicationError(Exception):
    """Base class for assessment application-layer failures."""


class AssignmentNotFoundError(AssessmentApplicationError):
    """Raised when a requested assignment does not exist."""


class PublishedAssignmentNotFoundError(AssessmentApplicationError):
    """Raised when a student requests an assignment that is not published."""
