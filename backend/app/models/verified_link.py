from datetime import datetime
from typing import Literal

from beanie import Document, PydanticObjectId
from pymongo import ASCENDING, IndexModel


class VerifiedLink(Document):
    owner_id: PydanticObjectId
    credential_id: PydanticObjectId
    consent_type: Literal["one_time", "per_request", "org_level", "time_bound"]
    bound_org_id: PydanticObjectId | None = None
    duration: Literal["24h", "7d", "30d", "permanent"] | None = None
    otp_hash: str
    expires_at: datetime | None = None
    status: Literal["active", "expired", "revoked"] = "active"
    view_count: int = 0
    deleted_at: datetime | None = None
    purge_after: datetime | None = None
    restored_at: datetime | None = None

    class Settings:
        name = "verified_links"
        indexes = [
            IndexModel(
                [("otp_hash", ASCENDING)],
                unique=True,
                partialFilterExpression={"status": "active"},
                name="uq_active_verified_link_otp_hash",
            ),
            IndexModel([("owner_id", ASCENDING), ("status", ASCENDING)]),
        ]
