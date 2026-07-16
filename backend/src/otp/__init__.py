"""Standalone OTP module: generation, storage, and verification.

Not responsible for sending emails/SMS, templates, or registration -
those belong to the Auth module and its Mailer service. This module
only ever returns a plain OTP code string; delivery is the caller's job.
"""

from .exceptions import (
    OtpAlreadyUsedError,
    OtpCodeMismatchError,
    OtpError,
    OtpExpiredError,
    OtpNotFoundError,
    OtpTypeMismatchError,
)
from .models import OtpCode, OtpType
from .repository import OtpRepository
from .service import OtpService

__all__ = [
    "OtpType",
    "OtpCode",
    "OtpRepository",
    "OtpService",
    "OtpError",
    "OtpNotFoundError",
    "OtpExpiredError",
    "OtpAlreadyUsedError",
    "OtpTypeMismatchError",
    "OtpCodeMismatchError",
]
