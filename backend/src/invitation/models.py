from datetime import UTC, datetime

from beanie import Document, PydanticObjectId
from pydantic import EmailStr, Field, PlainValidator, field_validator
from pymongo import ASCENDING, DESCENDING, IndexModel

from src.invitation.constants import InviteStatus
from src.models import utc_now


# 1. Định nghĩa kiểu dữ liệu tự động gắn múi giờ UTC nếu MongoDB trả về dạng naive datetime
def _ensure_timezone(value: object) -> object:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
    return value

AwareDatetimeWithDefault = Annotated[datetime, PlainValidator(_ensure_timezone)]


class InviteLink(Document):
    org_id: PydanticObjectId
    contact_email: EmailStr
    token_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: InviteStatus = InviteStatus.PENDING
    
    # 2. Thay AwareDatetime thành AwareDatetimeWithDefault
    expires_at: AwareDatetimeWithDefault
    created_by: PydanticObjectId
    created_at: AwareDatetimeWithDefault = Field(default_factory=utc_now)
    updated_at: AwareDatetimeWithDefault = Field(default_factory=utc_now)
    used_at: AwareDatetimeWithDefault | None = None
    revoked_at: AwareDatetimeWithDefault | None = None

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