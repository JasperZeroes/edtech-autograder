class GradingValidationError(ValueError):
    """Raised when deterministic grading data violates a domain invariant."""


class GradingCalculationError(GradingValidationError):
    """Raised when a grading score cannot be calculated safely."""
