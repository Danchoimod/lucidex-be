"""Mailer-specific exceptions."""


class EmailTemplateError(RuntimeError):
    """Raised when an email template cannot be resolved or loaded."""


class EmailDeliveryError(RuntimeError):
    """Raised when the SMTP provider cannot deliver an email."""

    def __init__(self, message: str = "Email delivery failed.") -> None:
        super().__init__(message)
