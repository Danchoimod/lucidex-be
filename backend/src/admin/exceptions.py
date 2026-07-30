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


class InactiveAdminAccountError(AppError):
    def __init__(
        self,
        message: str = "Admin account is not active.",
        *,
        log_context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            status_code=403,
            message=message,
            error_code="INACTIVE_ADMIN_ACCOUNT",
            log_context=log_context,
        )


class AdminLoginRateLimitError(AppError):
    def __init__(
        self,
        retry_after: int,
        *,
        log_context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            status_code=429,
            message="Too many login attempts. Please try again later.",
            error_code="ADMIN_LOGIN_RATE_LIMITED",
            log_context=log_context,
            headers={"Retry-After": str(max(1, retry_after))},
        )


class InvalidAdminTokenError(AppError):
    def __init__(self, *, log_context: dict[str, Any] | None = None) -> None:
        super().__init__(
            status_code=401,
            message="Invalid or expired token.",
            error_code="INVALID_ADMIN_TOKEN",
            log_context=log_context,
        )


class InvalidAuthenticationCodeError(AppError):
    def __init__(
        self,
        message: str = "Invalid authentication code.",
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
            message="Invalid Admin authentication state.",
            error_code="ADMIN_AUTHENTICATION_STATE_ERROR",
            log_context=log_context,
        )
