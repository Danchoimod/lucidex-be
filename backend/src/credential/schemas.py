from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.credential.constants import (
    DEFAULT_CREDENTIAL_SORT,
    DEFAULT_DEGREE_TYPE,
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


class OwnerCredentialIssuerDetail(BaseModel):
    id: str
    name: str
    address: str
    contact_email: str
    contact_phone: str


class OwnerCredentialDetail(BaseModel):
    id: str
    issuer_org_id: str
    issuer: OwnerCredentialIssuerDetail | None
    student_id: str
    class_id: str | None = None
    full_name: str
    dob: date
    major_vi: str | None = None
    major_en: str | None = None
    degree_type: str = DEFAULT_DEGREE_TYPE
    graduation_year: int
    graduation_classification_vi: str | None = None
    graduation_classification_en: str | None = None
    mode_of_study_vi: str | None = None
    mode_of_study_en: str | None = None
    university_email: str
    phone: str | None
    status: CredentialStatus
    claim_method: str | None
    claimed_at: datetime | None
    unclaimed_at: datetime | None = None
    revoked_reason: str | None = None
    revoked_at: datetime | None = None
    created_at: datetime | None = None
    restored_at: datetime | None = None


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


class CreateVerifiedLinkRequest(BaseModel):
    credential_id: str = Field(description="ObjectId string of the claimed credential.")
    expires_at: datetime | None = Field(default=None, description="ISO 8601 future expiration datetime, or None for Unlimited.")
    allowed_org_ids: list[str] = Field(default_factory=list, description="List of verifier org ObjectIds allowed, or empty for Unlimited.")
    max_access_count: int | None = Field(default=None, ge=1, description="Maximum access count (>= 1), or None for Unlimited.")

    model_config = ConfigDict(extra="forbid")


class VerifiedLinkResponse(BaseModel):
    id: str
    credential_id: str
    consent_mode: str | None = None
    expires_at: datetime | None = None
    allowed_org_ids: list[str] = Field(default_factory=list)
    max_access_count: int | None = None
    remaining_access_count: int | None = None
    display_status: str
    created_at: datetime
    revoked_at: datetime | None = None


class VerifiedLinkCreatedResponse(VerifiedLinkResponse):
    code: str = Field(description="Plaintext verification code — shown ONCE at creation.")


class VerifiedLinkListResponse(BaseModel):
    items: list[VerifiedLinkResponse]
    total: int
    page: int
    page_size: int



class RevokeVerifiedLinkResponse(BaseModel):
    id: str
    status: str
    revoked_at: datetime


class VerifyCodeRequest(BaseModel):
    code: str = Field(description="Plaintext verification code.")

    model_config = ConfigDict(extra="forbid")


class VerifyCodeCredentialData(BaseModel):
    id: str
    issuer_org_id: str
    issuer_name: str = ""
    student_id: str
    class_id: str | None = None
    full_name: str
    dob: date
    major: str = ""
    major_vi: str | None = None
    major_en: str | None = None
    graduation_year: int
    classification: str = ""
    graduation_classification_vi: str | None = None
    graduation_classification_en: str | None = None
    mode_of_study_vi: str | None = None
    mode_of_study_en: str | None = None
    degree_type: str = DEFAULT_DEGREE_TYPE
    university_email: str
    phone: str | None = None
    status: str
    claimed_at: datetime | None = None
    created_at: datetime | None = None


class VerifyCodeResponse(BaseModel):
    credential: VerifyCodeCredentialData | None = None
    verified_at: datetime | None = None

