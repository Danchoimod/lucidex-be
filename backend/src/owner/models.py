from datetime import date, datetime

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, EmailStr, Field
from pymongo import ASCENDING, IndexModel

from src.owner.constants import OwnerStatus, ConsentType, ConsentDuration


class ConsentSettings(BaseModel):
    default_type: ConsentType = ConsentType.ONE_TIME
    default_org_id: PydanticObjectId | None = None
    default_duration: ConsentDuration | None = None


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
