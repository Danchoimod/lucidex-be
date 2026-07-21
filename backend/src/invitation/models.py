from datetime import UTC, datetime

from beanie import Document, PydanticObjectId
from pydantic import AwareDatetime, EmailStr, Field, field_validator
from pymongo import ASCENDING, DESCENDING, IndexModel

from src.invitation.constants import InviteStatus
from src.models import utc_now


class InviteLink(Document):
    org_id: PydanticObjectId
    contact_email: EmailStr
    token_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: InviteStatus = InviteStatus.PENDING
    expires_at: AwareDatetime
    created_by: PydanticObjectId
    created_at: AwareDatetime = Field(default_factory=utc_now)
    updated_at: AwareDatetime = Field(default_factory=utc_now)
    used_at: AwareDatetime | None = None
    revoked_at: AwareDatetime | None = None

    @field_validator("contact_email", mode="before")
    @classmethod
    def normalize_contact_email(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator(
        "expires_at",
        "created_at",
        "updated_at",
        "used_at",
        "revoked_at",
        mode="before",
    )
    @classmethod
    def normalize_datetime(cls, value: object) -> object:
        if not isinstance(value, datetime):
            return value
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    class Settings:
        name = "invite_links"
        indexes = [
            IndexModel(
                [("token_hash", ASCENDING)],
                unique=True,
                name="uq_invite_token_hash",
            ),
            IndexModel(
                [("org_id", ASCENDING)],
                unique=True,
                partialFilterExpression={"status": InviteStatus.PENDING.value},
                name="uq_pending_invite_org",
            ),
            IndexModel(
                [
                    ("org_id", ASCENDING),
                    ("status", ASCENDING),
                    ("created_at", DESCENDING),
                ],
                name="ix_invite_org_status_created",
            ),
            IndexModel(
                [("expires_at", ASCENDING)],
                name="ix_invite_expires_at",
            ),
        ]
