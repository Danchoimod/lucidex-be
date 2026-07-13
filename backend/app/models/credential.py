from datetime import date, datetime
from typing import Literal

from beanie import Document, PydanticObjectId
from pymongo import ASCENDING, IndexModel


class Credential(Document):
    issuer_org_id: PydanticObjectId
    student_id: str
    full_name: str
    dob: date
    major: str
    graduation_year: int
    classification: str
    university_email: str
    national_id_hash: str | None = None
    phone: str | None = None
    status: Literal["unclaimed", "claimed", "revoked"] = "unclaimed"
    unclaimed_reason_code: Literal["AWAITING_CLAIM", "CLAIM_REJECTED"] | None = "AWAITING_CLAIM"
    owner_id: PydanticObjectId | None = None
    claim_method: Literal["university_email", "national_id"] | None = None
    claimed_at: datetime | None = None
    unclaimed_at: datetime | None = None
    revoked_reason: str | None = None
    revoked_by: PydanticObjectId | None = None
    revoked_at: datetime | None = None
    deleted_at: datetime | None = None
    purge_after: datetime | None = None
    restored_at: datetime | None = None

    class Settings:
        name = "credentials"
        indexes = [
            IndexModel(
                [("issuer_org_id", ASCENDING), ("student_id", ASCENDING)],
                unique=True,
            ),
            IndexModel([("national_id_hash", ASCENDING)]),
            IndexModel([("owner_id", ASCENDING), ("status", ASCENDING)]),
        ]
