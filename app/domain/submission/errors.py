class SubmissionValidationError(ValueError):
    """Raised when submission data violates a domain invariant."""


class InvalidSubmissionTransitionError(SubmissionValidationError):
    """Raised when a submission lifecycle transition is not permitted."""
