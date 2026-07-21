from src.exceptions import AppError


class InvalidAdminCredentialsError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=401,
            message="Invalid login credentials.",
            error_code="INVALID_ADMIN_CREDENTIALS",
        )


class InvalidAdminTokenError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=401,
            message="Invalid or expired authentication token.",
            error_code="INVALID_ADMIN_TOKEN",
        )


class InvalidAuthenticationCodeError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=401,
            message="Invalid authentication code. Please try again.",
            error_code="INVALID_AUTHENTICATION_CODE",
        )


class AdminAuthenticationStateError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=500,
            message="Admin authentication is not configured correctly.",
            error_code="ADMIN_AUTHENTICATION_STATE_ERROR",
        )
