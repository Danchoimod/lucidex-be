"""Organization module constants and enums."""

from enum import StrEnum


class OrganizationType(StrEnum):
    ISSUER = "issuer"
    VERIFIER = "verifier"


class OrganizationStatus(StrEnum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class AccountStatus(StrEnum):
    ACTIVE = "active"
    LOCKED = "locked"


LIVE_ORGANIZATION_STATUSES = (
    OrganizationStatus.PENDING_REVIEW.value,
    OrganizationStatus.APPROVED.value,
)