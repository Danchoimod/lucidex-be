from __future__ import annotations
from src.exceptions import AppError

class PasswordMismatchError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=400,
            message="Password and password confirmation do not match.",
            error_code="PASSWORD_MISMATCH",
        )

class WeakPasswordError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=400,
            message="Password must be at least 8 characters long and contain uppercase, lowercase, numbers, and special characters.",
            error_code="WEAK_PASSWORD",
        )

class AccountNotEligibleError(AppError):
    def __init__(self, message: str = "Account is not in a valid state to perform this action.") -> None:
        super().__init__(
            status_code=400,
            message=message,
            error_code="ACCOUNT_NOT_ELIGIBLE",
        )

class EmailSendingFailedError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=500,
            message="Failed to send verification OTP email. Please try again later.",
            error_code="EMAIL_SENDING_FAILED",
        )