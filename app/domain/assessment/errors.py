class AssessmentValidationError(ValueError):
    """Raised when assessment data violates a domain invariant."""


class AssignmentOwnershipError(PermissionError):
    """Raised when an instructor attempts to modify another assignment."""


class AssignmentNotReadyError(AssessmentValidationError):
    """Raised when an assignment cannot yet be published."""
