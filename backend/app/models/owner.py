from datetime import date, datetime
from typing import Literal

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, EmailStr, Field
from pymongo import ASCENDING, IndexModel


class ConsentSettings(BaseModel):
    default_type: Literal["one_time", "per_request", "org_level", "time_bound"] = "one_time"
    default_org_id: PydanticObjectId | None = None
    default_duration: Literal["24h", "7d", "30d", "permanent"] | None = None


class Owner(Document):
    email: EmailStr
    password_hash: str | None = None
    oauth_provider: str | None = None
    oauth_subject_id: str | None = None
    full_name: str | None = None
    phone: str | None = None
    avatar_url: str | None = None
    dob: date | None = None
    status: Literal["active", "locked_migrated", "soft_deleted"] = "active"
    consent_settings: ConsentSettings = Field(default_factory=ConsentSettings)
    deleted_at: datetime | None = None
    purge_after: datetime | None = None
    restored_at: datetime | None = None

    class Settings:
        name = "owners"
        indexes = [
            IndexModel([("email", ASCENDING)], unique=True),
            IndexModel(
                [("oauth_provider", ASCENDING), ("oauth_subject_id", ASCENDING)],
                unique=True,
                partialFilterExpression={
                    "oauth_provider": {"$exists": True},
                    "oauth_subject_id": {"$exists": True},
                },
                name="uq_owner_oauth_identity",
            ),
        ]
