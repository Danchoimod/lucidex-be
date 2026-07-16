"""Data access layer for OTP documents.

Built directly on Beanie's active-record API (`OtpCode.find/.insert/.save`)
rather than a raw Motor collection, since `OtpCode` is already bound to
the app's single MongoDB connection by `init_beanie()` in
`src.database.connect_database()`. No client/database is created or
injected here - this module simply reuses that existing connection.
"""

from __future__ import annotations

from typing import Optional

from .models import OtpCode, OtpType


class OtpRepository:
    """Encapsulates all persistence access for the OTP module."""

    async def insert(self, otp: OtpCode) -> OtpCode:
        """Persist a new OTP document."""
        return await otp.insert()

    async def find_latest_for_user(self, user_id: str) -> Optional[OtpCode]:
        """Return the most recently created OTP for a user, of any type.

        `verify_otp` inspects `type`/`otp_code`/`is_used`/`expired_at` on
        the returned document itself, so a type mismatch (e.g. user has an
        active LOGIN otp but verification was requested for
        RESET_PASSWORD) is reported precisely rather than as "not found".
        """
        return (
            await OtpCode.find(OtpCode.user_id == user_id)
            # created_at then _id (both desc): ObjectIds are monotonically
            # increasing, which breaks ties when two OTPs are created
            # within the same millisecond (e.g. immediate resend).
            .sort(-OtpCode.created_at, -OtpCode.id)
            .first_or_none()
        )

    async def mark_as_used(self, otp: OtpCode) -> None:
        """Flag an OTP document as used so it cannot be verified again."""
        otp.is_used = True
        await otp.save()

    async def invalidate_active(self, user_id: str, otp_type: OtpType) -> None:
        """Mark any still-unused OTPs of this type as used before issuing a new one.

        Prevents an old, still-unexpired code from remaining valid once a
        newer one has been requested.
        """
        await OtpCode.find(
            OtpCode.user_id == user_id,
            OtpCode.type == otp_type,
            OtpCode.is_used == False,  # noqa: E712 - Beanie needs `==`, not `is`
        ).update({"$set": {"is_used": True}})
