from datetime import datetime
from typing import Literal

from beanie import Document, PydanticObjectId
from pymongo import ASCENDING, IndexModel


class OwnerEkycIdentity(Document):
    owner_id: PydanticObjectId
    national_id_hash: str
    status: Literal["verified"] = "verified"
    provider: str | None = None
    verified_at: datetime

    class Settings:
        name = "owner_ekyc_identities"
        indexes = [
            IndexModel([("owner_id", ASCENDING)], unique=True),
            IndexModel(
                [
                    ("national_id_hash", ASCENDING),
                    ("status", ASCENDING),
                ],
                unique=True,
                name="uq_verified_national_id_hash",
            ),
        ]


class EkycCaptureSession(Document):
    owner_id: PydanticObjectId
    claim_id: PydanticObjectId
    token: str
    status: Literal[
        "pending", "submitted", "processing", "completed", "expired"
    ] = "pending"
    expires_at: datetime
    outcome: Literal[
        "auto_approved", "low_confidence", "unreadable_image", "liveness_failed"
    ] | None = None

    class Settings:
        name = "ekyc_capture_sessions"
        indexes = [
            IndexModel([("token", ASCENDING)], unique=True),
            IndexModel([("expires_at", ASCENDING)], expireAfterSeconds=0),
        ]
