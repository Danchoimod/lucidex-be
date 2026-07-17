from datetime import datetime

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field
from pymongo import ASCENDING, IndexModel

from src.auth.constants import ActorType, SessionStatus


class DeviceInfo(BaseModel):
    user_agent: str | None = None
    ip: str | None = None


class Session(Document):
    actor_type: ActorType
    actor_id: PydanticObjectId
    org_id: PydanticObjectId | None = None
    refresh_token_hash: str
    device_info: DeviceInfo = Field(default_factory=DeviceInfo)
    status: SessionStatus = SessionStatus.ACTIVE
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
