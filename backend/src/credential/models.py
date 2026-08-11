from datetime import date, datetime
from typing import Any, Literal

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field
from pymongo import ASCENDING, DESCENDING, IndexModel

from src.credential.constants import DEFAULT_DEGREE_TYPE
from src.models import utc_now


class Credential(Document):
    issuer_org_id: PydanticObjectId
    student_id: str
    full_name: str
    dob: date
    major: str = ""
    major_vi: str | None = None
    major_en: str | None = None
    graduation_year: int = Field(default_factory=lambda: datetime.now().year)
    classification: str = ""
    graduation_classification_vi: str | None = None
    graduation_classification_en: str | None = None
    mode_of_study: str | None = None
    mode_of_study_vi: str | None = None
    mode_of_study_en: str | None = None
    degree_type: str = DEFAULT_DEGREE_TYPE
    class_id: str | None = None
    university_email: str | None = None
    place_of_birth: str | None = None
    gender: str | None = None
    faculty: str | None = None
    specialization: str | None = None
    cpa: str | None = None
    degree_number: str | None = None
    register_number: str | None = None
    notes: str | None = None
    national_id_hash: str | None = None
    phone: str | None = None
    status: Literal["unclaimed", "claimed", "revoked"] = "unclaimed"
    unclaimed_reason_code: Literal["AWAITING_CLAIM", "CLAIM_REJECTED"] | None = (
        "AWAITING_CLAIM"
    )
    owner_id: PydanticObjectId | None = None
    claim_method: Literal["university_email", "national_id", "manual"] | None = None
    claimed_at: datetime | None = None
    unclaimed_at: datetime | None = None
    revoked_reason: str | None = None
    revoked_by: PydanticObjectId | None = None
    revoked_at: datetime | None = None
    created_at: datetime | None = None
    created_by: PydanticObjectId | None = None
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
            IndexModel(
                [
                    ("national_id_hash", ASCENDING),
                    ("status", ASCENDING),
                    ("owner_id", ASCENDING),
                ],
                name="ix_credential_unclaimed_match",
            ),
        ]


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


class VerifiedLink(Document):
    owner_id: PydanticObjectId
    credential_id: PydanticObjectId
    code: str = ""
    code_hash: str
    consent_mode: (
        Literal["access_count", "time_bound", "trusted_orgs", "custom"] | None
    ) = None
    expires_at: datetime | None = None
    allowed_org_ids: list[PydanticObjectId] = Field(default_factory=list)
    max_access_count: int | None = None
    remaining_access_count: int | None = None
    status: Literal["active", "expired", "revoked"] = "active"
    revoked_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    deleted_at: datetime | None = None
    purge_after: datetime | None = None
    restored_at: datetime | None = None

    class Settings:
        name = "verified_links"
        indexes = [
            IndexModel(
                [("code_hash", ASCENDING)],
                unique=True,
                partialFilterExpression={
                    "status": "active",
                    "otp_hash": {"$type": "string"},
                },
                name="uq_active_verified_link_otp_hash",
            ),
            IndexModel([("owner_id", ASCENDING), ("status", ASCENDING)]),
            IndexModel([("credential_id", ASCENDING)]),
        ]


class VerifiedLinkAccessLog(Document):
    link_id: PydanticObjectId
    owner_id: PydanticObjectId
    credential_id: PydanticObjectId
    verifier_org_id: PydanticObjectId
    verifier_account_id: PydanticObjectId
    verified_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "verified_link_access_logs"
        indexes = [
            IndexModel([("link_id", ASCENDING), ("verified_at", DESCENDING)]),
            IndexModel([("owner_id", ASCENDING), ("verified_at", DESCENDING)]),
            IndexModel([("verifier_org_id", ASCENDING), ("verified_at", DESCENDING)]),
        ]



class AccessRecord(Document):
    link_id: PydanticObjectId
    owner_id: PydanticObjectId
    verifier_org_id: PydanticObjectId
    credential_id: PydanticObjectId
    result: Literal["pending", "verified", "denied"]
    deny_reason: (
        Literal["expired", "revoked", "otp_invalid", "owner_declined"] | None
    ) = None
    consent_type_snapshot: Literal["one_time", "per_request", "org_level", "time_bound"]
    requested_at: datetime
    decided_at: datetime | None = None
    decided_by: PydanticObjectId | None = None
    viewed_at: datetime | None = None

    class Settings:
        name = "access_records"
        indexes = [
            IndexModel([("link_id", ASCENDING), ("viewed_at", DESCENDING)]),
            IndexModel([("verifier_org_id", ASCENDING), ("viewed_at", DESCENDING)]),
            IndexModel([("owner_id", ASCENDING), ("result", ASCENDING)]),
        ]


class CsvUploadJob(Document):
    org_id: PydanticObjectId
    filename: str
    total_rows: int = 0
    valid_count: int = 0
    error_count: int = 0
    created_count: int = 0
    status: Literal[
        "validating",
        "awaiting_confirmation",
        "processing",
        "completed",
        "failed",
    ] = "validating"
    overwrite_all: bool = False
    created_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "csv_upload_jobs"
        indexes = [
            IndexModel(
                [
                    ("org_id", ASCENDING),
                    ("status", ASCENDING),
                    ("created_at", DESCENDING),
                ],
                name="ix_csv_upload_job_resume",
            )
        ]


class CsvUploadRow(Document):
    job_id: PydanticObjectId
    seq_no: int
    student_id: str
    raw_payload: dict[str, Any]
    validation_status: Literal["valid", "invalid", "duplicate_pending", "resolved"]
    error_reason: str | None = None
    resolution: Literal["overwrite", "skip"] | None = None
    processing_status: Literal["queued", "created", "failed"] = "queued"

    class Settings:
        name = "csv_upload_rows"
        indexes = [
            IndexModel([("job_id", ASCENDING), ("validation_status", ASCENDING)]),
            IndexModel([("job_id", ASCENDING), ("student_id", ASCENDING)]),
        ]
