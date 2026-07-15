from datetime import datetime
from typing import Literal

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field
from pymongo import ASCENDING, IndexModel


class DeviceInfo(BaseModel):
    user_agent: str | None = None
    ip: str | None = None


class Session(Document):
    actor_type: Literal["owner", "institution_account", "platform_admin"]
    actor_id: PydanticObjectId
    org_id: PydanticObjectId | None = None
    refresh_token_hash: str
    device_info: DeviceInfo = Field(default_factory=DeviceInfo)
    status: Literal["active", "revoked"] = "active"
    twofa_verified: bool = False
    issued_at: datetime
    last_used_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None
    revoked_reason: str | None = None

    class Settings:
        name = "sessions"
        indexes = [
            IndexModel([("refresh_token_hash", ASCENDING)]),
            IndexModel([("actor_id", ASCENDING), ("status", ASCENDING)]),
            IndexModel([("expires_at", ASCENDING)], expireAfterSeconds=0),
        ]


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
