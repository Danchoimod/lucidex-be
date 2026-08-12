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
            status_code=409,
            message="This email is already registered.",
            error_code="EMAIL_ALREADY_REGISTERED",
        )


class PhoneAlreadyRegisteredError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=409,
            message="This phone number is already registered.",
            error_code="PHONE_ALREADY_REGISTERED",
        )


class OwnerNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=404,
            message="Owner not found.",
            error_code="OWNER_NOT_FOUND",
        )


class OwnerAlreadyActiveError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=400,
            message="Owner account is already active.",
            error_code="OWNER_ALREADY_ACTIVE",
        )


class InvalidOtpError(AppError):
    def __init__(self, message: str = "Invalid OTP code.") -> None:
        super().__init__(
            status_code=400,
            message=message,
            error_code="INVALID_OTP",
        )


class EmailSendingFailedError(AppError):
    def __init__(self, message: str = "Failed to send verification email.") -> None:
        super().__init__(
            status_code=500,
            message=message,
            error_code="EMAIL_SENDING_FAILED",
        )


class InvalidGoogleTokenError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=401,
            message="Invalid or expired Google token.",
            error_code="INVALID_GOOGLE_TOKEN",
        )


class GoogleEmailNotVerifiedError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=403,
            message="Google email is not verified.",
            error_code="GOOGLE_EMAIL_NOT_VERIFIED",
        )


class PasswordAccountOAuthLoginError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=409,
            message=(
                "This email is registered with a password. "
                "Please log in using your email and password."
            ),
            error_code="PASSWORD_ACCOUNT_OAUTH_LOGIN_NOT_ALLOWED",
        )


class GoogleAccountMismatchError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=409,
            message="Google account does not match the registered account.",
            error_code="GOOGLE_ACCOUNT_MISMATCH",
        )


class GoogleOAuthUnavailableError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=503,
            message="Google login is currently unavailable.",
            error_code="GOOGLE_OAUTH_UNAVAILABLE",
        )


class InvalidDefaultSettingsError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=422,
            message="Custom mode requires at least two of: max access count, expiry hours, allowed organizations.",
            error_code="INVALID_DEFAULT_SETTINGS",
        )


class InvalidNameError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=400,
            message="Please enter a valid name.",
            error_code="INVALID_FULL_NAME",
        )


class InvalidPhoneNumberError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=400,
            message="Please enter a valid phone number.",
            error_code="INVALID_PHONE_NUMBER",
        )


class InvalidAvatarFileError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=400,
            message="Please upload a valid image (JPG or PNG, max 5MB).",
            error_code="INVALID_AVATAR_FILE",
        )


