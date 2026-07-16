"""Mailer-specific exceptions."""


class EmailDeliveryError(RuntimeError):
    """Raised when the SMTP provider cannot deliver an email."""

    def __init__(self) -> None:
        super().__init__("Email delivery failed.")
