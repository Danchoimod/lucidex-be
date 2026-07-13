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
