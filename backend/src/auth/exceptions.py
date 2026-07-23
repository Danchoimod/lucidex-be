from src.exceptions import AppError


class InvalidCredentialsError(AppError):
    """Raised when authentication fails due to bad email or password."""

    def __init__(self) -> None:
        super().__init__(
            status_code=401,
            message="Invalid email or password.",
            error_code="INVALID_CREDENTIALS",
        )


class InactiveAccountError(AppError):
    """Raised when attempting to log into a pending or locked account."""

    def __init__(self, message: str = "Account is not active.") -> None:
        super().__init__(
            status_code=403,
            message=message,
            error_code="INACTIVE_ACCOUNT",
        )


class AccountNotFoundError(AppError):
    """Raised when attempting to log into a non-existent account."""

    def __init__(self, message: str = "Account does not exist.") -> None:
        super().__init__(
            status_code=404,
            message=message,
            error_code="ACCOUNT_NOT_FOUND",
        )


class GoogleAccountPasswordLoginNotAllowedError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=409,
            message="This email is registered via Google. Please log in using Google.",
            error_code="GOOGLE_ACCOUNT_PASSWORD_LOGIN_NOT_ALLOWED",
        )


class InvalidOtpError(AppError):
    """Raised when OTP verification fails during login."""

    def __init__(self, message: str = "Invalid OTP code.") -> None:
        super().__init__(
            status_code=400,
            message=message,
            error_code="INVALID_OTP",
        )
