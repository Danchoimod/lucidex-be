from datetime import datetime
from typing import Literal

from beanie import Document, PydanticObjectId
from pymongo import ASCENDING, IndexModel


class OtpCode(Document):
    subject_type: Literal[
        "owner", "institution_account", "verified_link", "pending_registration"
    ]
    subject_id: PydanticObjectId | str
    purpose: Literal[
        "2fa_login", "register", "claim_email", "password_reset", "link_access"
    ]
    code_hash: str
    channel: Literal["email", "sms"]
    attempts: int = 0
    max_attempts: int = 5
    expires_at: datetime
    used: bool = False

    class Settings:
        name = "otp_codes"
        indexes = [IndexModel([("expires_at", ASCENDING)], expireAfterSeconds=0)]
