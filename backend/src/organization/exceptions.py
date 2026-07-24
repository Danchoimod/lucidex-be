"""Organization module exceptions."""

from src.exceptions import AppError


class TaxCodeAlreadyRegisteredError(AppError):
    """Raised when an issuer/verifier tax code already has a live registration."""

    def __init__(self) -> None:
        super().__init__(
            status_code=409,
            message="A live registration with this tax code already exists.",
            error_code="TAX_CODE_ALREADY_REGISTERED",
        )


class ContactEmailAlreadyRegisteredError(AppError):
    """Raised when an issuer/verifier contact email already has a live registration."""

    def __init__(self) -> None:
        super().__init__(
            status_code=411,
            message="A live registration with this contact email already exists.",
            error_code="EMAIL_ALREADY_REGISTERED",
        )


class ContactPhoneAlreadyRegisteredError(AppError):
    """Raised when an issuer/verifier contact phone number already has a live registration."""

    def __init__(self) -> None:
        super().__init__(
            status_code=410,
            message="A live registration with this contact phone number already exists.",
            error_code="PHONE_ALREADY_REGISTERED",
        )


class OrganizationEmailSendingFailedError(AppError):
    """Raised when the registration confirmation email fails to send."""

    def __init__(self) -> None:
        super().__init__(
            status_code=502,
            message="Failed to send registration confirmation email.",
            error_code="ORGANIZATION_EMAIL_SENDING_FAILED",
        )