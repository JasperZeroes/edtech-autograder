class CodeExecutionError(RuntimeError):
    """Base class for isolated execution infrastructure failures."""


class CodeExecutionUnavailableError(CodeExecutionError):
    """Raised when the external execution service cannot be reached."""


class CodeExecutionProtocolError(CodeExecutionError):
    """Raised when the execution service returns an invalid response."""
