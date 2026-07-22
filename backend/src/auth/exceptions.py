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

    def __init__(self, message: str = "Tài khoản không tồn tại.") -> None:
        super().__init__(
            status_code=404,
            message=message,
            error_code="ACCOUNT_NOT_FOUND",
        )
