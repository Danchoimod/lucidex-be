from datetime import datetime
from typing import Literal

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field
from pymongo import ASCENDING, IndexModel


class EkycAttempt(BaseModel):
    attempt_no: int
    ocr_score: float
    face_match_score: float
    liveness_passed: bool
    national_id_hash: str
    combined_score: float
    outcome: Literal[
        "auto_approved",
        "low_confidence",
        "unreadable_image",
        "liveness_failed",
    ]
    attempted_at: datetime


class Claim(Document):
    owner_id: PydanticObjectId
    credential_id: PydanticObjectId
    issuer_org_id: PydanticObjectId
    method: Literal["university_email", "cccd_ekyc"]
    status: Literal[
        "otp_pending", "pending_review", "approved", "rejected", "needs_info"
    ]
    ekyc_attempts: list[EkycAttempt] = Field(default_factory=list, max_length=4)
    scan_retry_count: int = Field(default=0, ge=0, le=3)
    rejection_reason: str | None = None
    reviewed_by: PydanticObjectId | None = None
    reviewed_at: datetime | None = None
    migrated_from_owner_id: PydanticObjectId | None = None
    queue_entered_at: datetime | None = None

    class Settings:
        name = "claims"
        indexes = [
            IndexModel(
                [
                    ("issuer_org_id", ASCENDING),
                    ("status", ASCENDING),
                    ("queue_entered_at", ASCENDING),
                ],
                name="ix_claim_review_queue",
            ),
            IndexModel(
                [("owner_id", ASCENDING), ("status", ASCENDING)],
                name="ix_claim_owner_status",
            ),
            IndexModel([("credential_id", ASCENDING)], name="ix_claim_credential"),
        ]
