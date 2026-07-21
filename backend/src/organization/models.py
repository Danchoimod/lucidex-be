from datetime import datetime
from typing import Literal

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, EmailStr, Field
from pymongo import ASCENDING, IndexModel

from src.models import utc_now
from src.organization.constants import (
    LIVE_ORGANIZATION_STATUSES,
    AccountStatus,
    InstitutionRole,
    OrganizationStatus,
    OrganizationType,
)


class OrganizationDocument(BaseModel):
    """A single uploaded document (e.g. license PDF).
    Populated by the file-upload service (Google Cloud Storage) — not by
    the registration flow. This flow only reserves the field/shape.
    """

    name: str
    url: str
    type: str


class VerifierPlan(BaseModel):
    """Quota/subscription plan info — verifier organizations only."""

    tier: str | None = None
    monthly_quota: int | None = None
    quota_used: int = 0
    reset_at: datetime | None = None


class VerifierProfile(BaseModel):
    """Reserved for future verifier-specific profile data."""

    pass


class InstitutionAccount(Document):
    org_id: PydanticObjectId
    email: EmailStr
    password_hash: str
    role: InstitutionRole = InstitutionRole.ADMIN
    twofa_method: Literal["email", "sms", "totp"] | None = None
    twofa_enabled: bool = False
    status: AccountStatus = AccountStatus.ACTIVE

    class Settings:
        name = "institution_accounts"
        indexes = [
            IndexModel([("email", ASCENDING)], unique=True),
            IndexModel([("org_id", ASCENDING)]),
        ]


class TrustedOrganization(Document):
    """Reserved placeholder for trusted organization references."""

    pass


class Organization(Document):
    type: OrganizationType
    status: OrganizationStatus = OrganizationStatus.PENDING_REVIEW
    name: str
    tax_code: str
    address: str
    legal_rep_name: str
    contact_email: EmailStr
    contact_phone: str
    registrant_name: str
    registrant_title: str | None = None
    documents: list[OrganizationDocument] = Field(default_factory=list)
    rejection_reason: str | None = None
    reviewed_by: PydanticObjectId | None = None
    reviewed_at: datetime | None = None
    account_status: AccountStatus = AccountStatus.ACTIVE
    lock_reason: str | None = None
    locked_by: PydanticObjectId | None = None
    locked_at: datetime | None = None
    verifier_profile: VerifierProfile | None = None
    plan: VerifierPlan | None = None
    created_at: datetime = Field(default_factory=utc_now)
    deleted_at: datetime | None = None
    purge_after: datetime | None = None
    restored_at: datetime | None = None

    class Settings:
        name = "organizations"
        indexes = [
            IndexModel(
                [("tax_code", ASCENDING), ("type", ASCENDING)],
                unique=True,
                partialFilterExpression={
                    "status": {"$in": list(LIVE_ORGANIZATION_STATUSES)}
                },
                name="uq_live_organization_tax_code_type",
            ),
            IndexModel(
                [("status", ASCENDING), ("type", ASCENDING), ("created_at", ASCENDING)],
                name="ix_organization_review_queue",
            ),
        ]
