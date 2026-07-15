from enum import StrEnum


class OrganizationStatus(StrEnum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


LIVE_ORGANIZATION_STATUSES = (
    OrganizationStatus.PENDING_REVIEW.value,
    OrganizationStatus.APPROVED.value,
)
