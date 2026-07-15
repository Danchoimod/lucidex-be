from datetime import datetime
from typing import Literal

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, EmailStr, Field
from pymongo import ASCENDING, IndexModel

from app.models.base import utc_now
from app.models.enums import LIVE_ORGANIZATION_STATUSES, OrganizationStatus


class OrganizationDocument(BaseModel):
    name: str
    url: str
    type: str


class VerifierPlan(BaseModel):
    tier: str | None = None
    monthly_quota: int | None = None
    quota_used: int = 0
    reset_at: datetime | None = None


class VerifierProfile(BaseModel):
    plan: VerifierPlan = Field(default_factory=VerifierPlan)


class Organization(Document):
    type: Literal["issuer", "verifier"]
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
    invite_token: str | None = None
    invite_token_used: bool = False
    account_status: Literal["active", "locked"] = "active"
    lock_reason: str | None = None
    locked_by: PydanticObjectId | None = None
    locked_at: datetime | None = None
    verifier_profile: VerifierProfile | None = None
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
