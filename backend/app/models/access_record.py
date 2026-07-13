from datetime import datetime
from typing import Literal

from beanie import Document, PydanticObjectId
from pymongo import ASCENDING, DESCENDING, IndexModel


class AccessRecord(Document):
    link_id: PydanticObjectId
    owner_id: PydanticObjectId
    verifier_org_id: PydanticObjectId
    credential_id: PydanticObjectId
    result: Literal["pending", "verified", "denied"]
    deny_reason: Literal[
        "expired", "revoked", "otp_invalid", "owner_declined"
    ] | None = None
    consent_type_snapshot: Literal[
        "one_time", "per_request", "org_level", "time_bound"
    ]
    requested_at: datetime
    decided_at: datetime | None = None
    decided_by: PydanticObjectId | None = None
    viewed_at: datetime | None = None

    class Settings:
        name = "access_records"
        indexes = [
            IndexModel([("link_id", ASCENDING), ("viewed_at", DESCENDING)]),
            IndexModel(
                [("verifier_org_id", ASCENDING), ("viewed_at", DESCENDING)]
            ),
            IndexModel([("owner_id", ASCENDING), ("result", ASCENDING)]),
        ]
