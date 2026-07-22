from typing import Any

from src.exceptions import AppError


class InvalidAdminCredentialsError(AppError):
    def __init__(self, *, log_context: dict[str, Any] | None = None) -> None:
        super().__init__(
            status_code=401,
            message="Invalid username or password.",
            error_code="INVALID_ADMIN_CREDENTIALS",
            log_context=log_context,
        )


class InvalidAdminTokenError(AppError):
    def __init__(self, *, log_context: dict[str, Any] | None = None) -> None:
        super().__init__(
            status_code=401,
            message="Invalid or expired authentication token.",
            error_code="INVALID_ADMIN_TOKEN",
            log_context=log_context,
        )


class InvalidAuthenticationCodeError(AppError):
    def __init__(
        self,
        message: str = "Invalid authentication code. Please try again.",
        *,
        log_context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            status_code=401,
            message=message,
            error_code="INVALID_AUTHENTICATION_CODE",
            log_context=log_context,
        )


class AdminAuthenticationStateError(AppError):
    def __init__(self, *, log_context: dict[str, Any] | None = None) -> None:
        super().__init__(
            status_code=500,
            message="Admin authentication is not configured correctly.",
            error_code="ADMIN_AUTHENTICATION_STATE_ERROR",
            log_context=log_context,
        )
