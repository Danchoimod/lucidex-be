from src.exceptions import AppError


class PasswordMismatchError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=400,
            message="Password and Confirm Password do not match.",
            error_code="PASSWORD_MISMATCH",
        )


class WeakPasswordError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=400,
            message="Password must contain at least 8 characters, 1 uppercase letter, 1 lowercase letter, 1 number, and 1 special character.",
            error_code="WEAK_PASSWORD",
        )


class EmailAlreadyRegisteredError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=400,
            message="This email is already registered.",
            error_code="EMAIL_ALREADY_REGISTERED",
        )
