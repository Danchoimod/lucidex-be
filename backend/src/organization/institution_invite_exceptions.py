from __future__ import annotations
from src.exceptions import AppError

class PasswordMismatchError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=400,
            message="Mật khẩu và xác nhận mật khẩu không khớp.",
            error_code="PASSWORD_MISMATCH",
        )

class WeakPasswordError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=400,
            message="Mật khẩu phải có ít nhất 8 ký tự, bao gồm chữ hoa, chữ thường, số và ký tự đặc biệt.",
            error_code="WEAK_PASSWORD",
        )

class AccountNotEligibleError(AppError):
    def __init__(self, message: str = "Tài khoản không ở trạng thái hợp lệ để thực hiện thao tác này.") -> None:
        super().__init__(
            status_code=400,
            message=message,
            error_code="ACCOUNT_NOT_ELIGIBLE",
        )

class EmailSendingFailedError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=500,
            message="Không thể gửi email chứa mã xác thực OTP. Vui lòng thử lại sau.",
            error_code="EMAIL_SENDING_FAILED",
        )