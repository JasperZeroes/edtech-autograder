class IdentityApplicationError(Exception):
    """Base class for identity application-layer errors."""


class DuplicateEmailError(IdentityApplicationError):
    """Raised when registration attempts to reuse an existing email address."""


class InvalidPasswordError(IdentityApplicationError):
    """Raised when a registration password violates the supported policy."""


class InvalidCredentialsError(IdentityApplicationError):
    """Raised when supplied login credentials cannot authenticate a user."""


class InactiveUserError(IdentityApplicationError):
    """Raised when valid credentials belong to a deactivated user."""


class InvalidTokenError(IdentityApplicationError):
    """Raised when an authentication token cannot be trusted or decoded."""


class ExpiredTokenError(InvalidTokenError):
    """Raised when an otherwise valid token has expired."""
