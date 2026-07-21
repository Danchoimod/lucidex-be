"""Domain exceptions for the OTP module.

Kept independent of `src.exceptions` (HTTP-facing) so this module stays
importable without a request context. The Auth module is expected to
catch these and translate them into the appropriate HTTP response.
"""


class OtpError(Exception):
    """Base class for all OTP-related errors."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class OtpNotFoundError(OtpError):
    """No OTP record exists for the given user."""

    def __init__(self, message: str = "OTP not found.") -> None:
        super().__init__(message)


class OtpExpiredError(OtpError):
    """The OTP was found but is past its `expired_at` timestamp."""

    def __init__(self, message: str = "OTP has expired.") -> None:
        super().__init__(message)


class OtpAlreadyUsedError(OtpError):
    """The OTP was found but has already been consumed once."""

    def __init__(self, message: str = "OTP has already been used.") -> None:
        super().__init__(message)


class OtpTypeMismatchError(OtpError):
    """The OTP found for the user does not match the requested `type`."""

    def __init__(self, message: str = "OTP type does not match.") -> None:
        super().__init__(message)


class OtpCodeMismatchError(OtpError):
    """The submitted `otp_code` does not match the stored value."""

    def __init__(self, message: str = "OTP code does not match.") -> None:
        super().__init__(message)
