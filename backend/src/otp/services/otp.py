"""Business logic for generating, issuing, and verifying OTPs."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from src.otp.exceptions import (
    OtpAlreadyUsedError,
    OtpCodeMismatchError,
    OtpExpiredError,
    OtpNotFoundError,
    OtpTypeMismatchError,
)
from src.otp.models import OtpCode, OtpType
from src.otp.repository import OtpRepository

DEFAULT_OTP_LENGTH = 6
DEFAULT_EXPIRY_MINUTES = 5
ALLOWED_OTP_LENGTHS = (6,)


class OtpService:
    """Public API of the OTP module. Auth is the only expected caller."""

    def __init__(
        self,
        repository: OtpRepository | None = None,
        expiry_minutes: int = DEFAULT_EXPIRY_MINUTES,
    ) -> None:
        self._repository = repository or OtpRepository()
        self._expiry_minutes = expiry_minutes

    @staticmethod
    def generate_otp(length: int = DEFAULT_OTP_LENGTH) -> str:
        """Generate a random numeric OTP, zero-padded to `length` digits.

        Uses `secrets.randbelow` (CSPRNG) instead of `random` since OTPs
        are a security control, not just a display value.
        """
        if length not in ALLOWED_OTP_LENGTHS:
            raise ValueError("OTP length must be 6 digits.")
        upper_bound = 10**length
        return str(secrets.randbelow(upper_bound)).zfill(length)

    async def create_otp(self, user_id: str, otp_type: str) -> str:
        """Generate and persist a new OTP for a user, returning the code.

        Any previously active (unused) OTP of the same type for this user
        is invalidated first, so at most one active code exists per
        (user_id, type) at a time. Only the raw code is returned - the
        Auth module is responsible for delivering it (email/SMS).
        """
        otp_type_enum = _to_otp_type(otp_type)
        await self._repository.invalidate_active(user_id, otp_type_enum)

        now = datetime.now(timezone.utc)
        record = OtpCode(
            user_id=user_id,
            otp_code=self.generate_otp(),
            type=otp_type_enum,
            created_at=now,
            expired_at=now + timedelta(minutes=self._expiry_minutes),
            is_used=False,
        )
        await self._repository.insert(record)
        return record.otp_code

    async def verify_otp(self, user_id: str, otp_code: str, otp_type: str) -> bool:
        """Verify an OTP for a user, raising a specific error per failure mode.

        Checks, in order: existence, expiry, reuse, type match, code
        match. Returns True only if all checks pass, and marks the OTP
        as used so it can't be replayed.
        """
        otp_type_enum = _to_otp_type(otp_type)

        document = await self._repository.find_latest_for_user(user_id)
        if document is None:
            raise OtpNotFoundError()

        if _as_aware_utc(document.expired_at) < datetime.now(timezone.utc):
            raise OtpExpiredError()

        if document.is_used:
            raise OtpAlreadyUsedError()

        if document.type != otp_type_enum:
            raise OtpTypeMismatchError()

        if document.otp_code != otp_code:
            raise OtpCodeMismatchError()

        await self._repository.mark_as_used(document)
        return True


def _to_otp_type(otp_type: str | OtpType) -> OtpType:
    """Coerce the plain-string `otp_type` param into the `OtpType` enum."""
    if isinstance(otp_type, OtpType):
        return otp_type
    try:
        return OtpType(otp_type)
    except ValueError as exc:
        raise ValueError(f"Unsupported OTP type: {otp_type!r}") from exc


def _as_aware_utc(value: datetime) -> datetime:
    """Normalize a possibly-naive datetime to a UTC-aware one."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


otp_service = OtpService()
