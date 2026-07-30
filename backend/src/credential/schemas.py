from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.credential.constants import (
    DEFAULT_CREDENTIAL_SORT,
    DEFAULT_PAGE,
    DEFAULT_PAGE_LIMIT,
    MAX_PAGE_LIMIT,
    OWNER_CREDENTIAL_SORT_FIELDS,
    CredentialStatus,
    OwnerCredentialStatus,
)


class OwnerCredentialListQuery(BaseModel):
    page: int = Field(default=DEFAULT_PAGE, ge=1, description="Page number.")
    limit: int = Field(
        default=DEFAULT_PAGE_LIMIT,
        ge=1,
        le=MAX_PAGE_LIMIT,
        description="Items per page, up to 100.",
    )
    student_id: str | None = Field(
        default=None,
        max_length=100,
        description="Exact student ID filter.",
    )
    graduation_year: int | None = Field(
        default=None,
        ge=1900,
        le=2200,
        description="Exact graduation year filter.",
    )
    status: OwnerCredentialStatus | None = Field(
        default=None,
        description="Filter the authorized set by claimed or unclaimed status.",
    )
    search: str | None = Field(
        default=None,
        max_length=100,
        description="Case-insensitive literal search over allowlisted fields.",
    )
    sort: str = Field(
        default=DEFAULT_CREDENTIAL_SORT,
        description="Allowlisted field and direction in field:asc|desc format.",
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("student_id", "search")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("sort")
    @classmethod
    def validate_sort(cls, value: str) -> str:
        parts = value.split(":")
        if (
            len(parts) != 2
            or parts[0] not in OWNER_CREDENTIAL_SORT_FIELDS
            or parts[1] not in {"asc", "desc"}
        ):
            raise ValueError(
                "Sort must use an allowed field and asc or desc direction."
            )
        return value

    def sort_parts(self) -> tuple[str, int]:
        field, direction = self.sort.split(":")
        return field, 1 if direction == "asc" else -1


class OwnerCredentialListItem(BaseModel):
    id: str
    student_id: str
    full_name: str
    graduation_year: int
    status: CredentialStatus
    can_claim: bool
    claimed_at: datetime | None


class OwnerCredentialSummary(BaseModel):
    total_credentials: int
    total_claimed: int
    total_unclaimed: int


class OwnerCredentialPagination(BaseModel):
    page: int
    limit: int
    total_items: int
    total_pages: int


class OwnerCredentialListData(BaseModel):
    summary: OwnerCredentialSummary
    items: list[OwnerCredentialListItem]
    pagination: OwnerCredentialPagination


class OwnerCredentialDetail(BaseModel):
    id: str
    issuer_org_id: str
    student_id: str
    full_name: str
    dob: date
    major: str
    graduation_year: int
    classification: str
    university_email: str
    phone: str | None
    status: CredentialStatus
    claim_method: str | None
    claimed_at: datetime | None


class ClaimCredentialRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ClaimedCredentialData(BaseModel):
    id: str
    status: CredentialStatus
    claim_method: str | None
    claimed_at: datetime | None


class ClaimCredentialData(BaseModel):
    credential: ClaimedCredentialData
    already_claimed: bool
