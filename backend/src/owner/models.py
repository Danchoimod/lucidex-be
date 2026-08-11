from datetime import date, datetime

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, EmailStr, Field
from pymongo import ASCENDING, IndexModel

from src.owner.constants import OwnerStatus


class DefaultLinkSettings(BaseModel):
    default_consent_mode: str | None = None
    default_max_access_count: int | None = None
    default_expiry_hours: int | None = None
    default_allowed_org_ids: list[PydanticObjectId] = Field(default_factory=list)


class Owner(Document):
    email: EmailStr
    password_hash: str | None = None
    oauth_provider: str | None = None
    oauth_subject_id: str | None = None
    full_name: str | None = None
    phone: str | None = None
    avatar_url: str | None = None
    dob: date | None = None
    status: OwnerStatus = OwnerStatus.PENDING
    default_link_settings: DefaultLinkSettings = Field(default_factory=DefaultLinkSettings)
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
                    "oauth_provider": {"$type": "string"},
                    "oauth_subject_id": {"$type": "string"},
                },
                name="uq_owner_oauth_identity",
            ),
        ]
