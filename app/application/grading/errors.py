class CodeExecutionError(RuntimeError):
    """Base class for isolated execution infrastructure failures."""


class CodeExecutionUnavailableError(CodeExecutionError):
    """Raised when the external execution service cannot be reached."""


class CodeExecutionProtocolError(CodeExecutionError):
    """Raised when the execution service returns an invalid response."""


class GradingWorkflowError(RuntimeError):
    """Base class for grading orchestration failures."""


class GradingSubmissionNotFoundError(GradingWorkflowError):
    """Raised when a worker receives an unknown submission id."""


class GradingAssignmentNotFoundError(GradingWorkflowError):
    """Raised when persisted submission data references no assignment."""


class GradingResultMissingError(GradingWorkflowError):
    """Raised when a completed submission has no persisted result."""


class SubmissionAlreadyRunningError(GradingWorkflowError):
    """Raised when another worker is already grading a submission."""
