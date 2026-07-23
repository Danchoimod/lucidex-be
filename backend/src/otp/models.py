"""Beanie Document for the OTP module.

Mirrors the schema:

    {
      "_id": ObjectId,
      "user_id": str,
      "otp_code": str,
      "type": "VERIFY_EMAIL" | "RESET_PASSWORD" | "LOGIN",
      "created_at": datetime,
      "expired_at": datetime,
      "is_used": bool
    }
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from beanie import Document
from pymongo import ASCENDING, DESCENDING, IndexModel


class OtpType(str, Enum):
    """Supported OTP purposes."""

    VERIFY_EMAIL = "VERIFY_EMAIL"
    RESET_PASSWORD = "RESET_PASSWORD"
    LOGIN = "LOGIN"
    INSTITUTION_INVITE = "INSTITUTION_INVITE"

class OtpCode(Document):
    """A single OTP issued to a user for a specific purpose.

    `otp_code` is always a string (never a number) so codes with a
    leading zero, e.g. "0142", are preserved exactly as generated.
    """

    user_id: str
    otp_code: str
    type: OtpType
    created_at: datetime
    expired_at: datetime
    is_used: bool = False

    class Settings:
        name = "otp_codes"
        indexes = [
            # Supports "latest OTP for this user" lookups used by verify_otp.
            IndexModel(
                [
                    ("user_id", ASCENDING),
                    ("type", ASCENDING),
                    ("created_at", DESCENDING),
                ],
                name="user_type_created_idx",
            ),
            # Automatically delete OTP documents 7 days after creation
            IndexModel(
                [("created_at", ASCENDING)],
                expireAfterSeconds=7 * 24 * 3600,  # 7 days in seconds
                name="created_at_ttl_7d_idx",
            ),
        ]

