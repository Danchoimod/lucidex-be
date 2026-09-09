"""Issuer schemas entry point."""

from pydantic import BaseModel, Field

from src.credential.constants import DEFAULT_DEGREE_TYPE
from src.organization.institution_invite_schemas import (
    GenericApiResponse,
    OtpVerifyRequest,
    PasswordSubmitRequest,
)
from src.organization.schemas import IssuerRegistrationData, IssuerRegistrationRequest


class CredentialImportData(BaseModel):
    """Response data for credential CSV import statistics."""

    total_received: int = Field(..., description="Total rows received in CSV")
    created_count: int = Field(..., description="Number of new credentials created")
    updated_count: int = Field(..., description="Number of credentials updated/overwritten")
    skipped_count: int = Field(..., description="Number of duplicate credentials skipped")
    storage_path: str | None = Field(default=None, description="Storage path or public URL of uploaded CSV file")


class ExistingCredentialData(BaseModel):
    full_name: str
    dob: str
    major: str | None = None
    major_vi: str | None = None
    major_en: str | None = None
    graduation_year: int
    classification: str | None = None
    graduation_classification_vi: str | None = None
    graduation_classification_en: str | None = None
    mode_of_study: str | None = None
    mode_of_study_vi: str | None = None
    mode_of_study_en: str | None = None
    university_email: str | None = None
    place_of_birth: str | None = None
    gender: str | None = None
    degree_type: str | None = None
    faculty: str | None = None
    specialization: str | None = None
    cpa: str | None = None
    degree_number: str | None = None
    register_number: str | None = None
    notes: str | None = None
    national_id_hash: str | None = None


class IncomingCredentialData(BaseModel):
    full_name: str
    dob: str
    major: str | None = None
    major_vi: str | None = None
    major_en: str | None = None
    graduation_year: int
    classification: str | None = None
    graduation_classification_vi: str | None = None
    graduation_classification_en: str | None = None
    mode_of_study: str | None = None
    mode_of_study_vi: str | None = None
    mode_of_study_en: str | None = None
    university_email: str | None = None
    place_of_birth: str | None = None
    gender: str | None = None
    degree_type: str | None = None
    faculty: str | None = None
    specialization: str | None = None
    cpa: str | None = None
    degree_number: str | None = None
    register_number: str | None = None
    notes: str | None = None
    national_id_hash: str | None = None


class DuplicateCredentialItemData(BaseModel):
    row_number: int
    student_id: str
    class_code: str
    existing: ExistingCredentialData
    incoming: IncomingCredentialData


class CheckDuplicatesData(BaseModel):
    total_rows: int
    has_duplicates: bool
    duplicate_count: int
    duplicate_ratio: float | None = None
    duplicates: list[DuplicateCredentialItemData] = Field(default_factory=list)


class ManualCredentialCreateRequest(BaseModel):
    student_id: str = Field(..., description="Student ID")
    full_name: str = Field(..., description="Full Name")
    dob: str = Field(..., description="Date of birth (YYYY-MM-DD or DD/MM/YYYY)")
    graduation_year: int = Field(default_factory=lambda: 2026, description="Graduation year")
    university_email: str | None = Field(default=None, description="University email")
    major: str | None = Field(default=None, description="Ngành học")
    classification: str | None = Field(default=None, description="Xếp loại tốt nghiệp")
    mode_of_study: str | None = Field(default=None, description="Hình thức đào tạo")
    degree_type: str | None = Field(default=None, description="Loại bằng (Cử nhân, Kỹ sư, Thạc sĩ, Tiến sĩ)")
    class_id: str | None = Field(default=None, description="Class ID")
    place_of_birth: str | None = Field(default=None, description="Place of birth")
    gender: str | None = Field(default=None, description="Gender")
    faculty: str | None = Field(default=None, description="Faculty / Department")
    specialization: str | None = Field(default=None, description="Specialization")
    cpa: str | None = Field(default=None, description="CPA / GPA")
    degree_number: str | None = Field(default=None, description="Degree number")
    register_number: str | None = Field(default=None, description="Book register number")
    notes: str | None = Field(default=None, description="Notes")
    national_id_hash: str | None = Field(default=None, description="Hashed National ID")
    phone: str | None = Field(default=None, description="Phone number")
    overwrite: bool = Field(default=False, description="Set to true to overwrite existing credential if present")


class ManualCredentialResponseData(BaseModel):
    id: str = Field(..., description="Credential ID")
    student_id: str = Field(..., description="Student ID")
    full_name: str = Field(..., description="Full Name")
    status: str = Field(..., description="Credential status")
    action: str = Field(..., description="'created' or 'updated'")


class CredentialSummaryData(BaseModel):
    total_credentials: int = Field(..., description="Total credentials matching filter")
    total_claimed: int = Field(..., description="Total claimed credentials in filtered set")
    total_unclaimed: int = Field(..., description="Total unclaimed credentials in filtered set")


class CredentialListItemData(BaseModel):
    id: str = Field(..., description="Credential ID")
    student_id: str = Field(..., description="Student ID")
    class_id: str | None = Field(default=None, description="Class ID")
    full_name: str = Field(..., description="Full Name")
    graduation_year: int = Field(..., description="Graduation year")
    status: str = Field(..., description="Status ('claimed' or 'unclaimed')")
    claimed_at: str | None = Field(default=None, description="Claimed timestamp in ISO format")
    created_at: str | None = Field(default=None, description="Created timestamp in ISO format")


class CredentialPaginationData(BaseModel):
    page: int = Field(..., description="Current page number")
    limit: int = Field(..., description="Items per page")
    total_items: int = Field(..., description="Total items matching filter")
    total_pages: int = Field(..., description="Total pages available")


class IssuerCredentialListData(BaseModel):
    summary: CredentialSummaryData
    items: list[CredentialListItemData]
    pagination: CredentialPaginationData


class IssuerCredentialDetailData(BaseModel):
    id: str = Field(..., description="Credential ID")
    issuer_org_id: str = Field(..., description="Issuer organization ID")
    student_id: str = Field(..., description="Student ID")
    class_id: str | None = Field(default=None, description="Class ID")
    full_name: str = Field(..., description="Full Name")
    dob: str = Field(..., description="Date of birth in YYYY-MM-DD format")
    major: str | None = Field(default=None, description="Major name")
    degree_type: str = Field(
        default=DEFAULT_DEGREE_TYPE,
        description="Degree type",
    )
    graduation_year: int = Field(..., description="Graduation year")
    classification: str | None = Field(default=None, description="Graduation classification")
    mode_of_study: str | None = Field(default=None, description="Mode of study")
    university_email: str | None = Field(default=None, description="University email")
    place_of_birth: str | None = Field(default=None, description="Place of birth")
    gender: str | None = Field(default=None, description="Gender")
    faculty: str | None = Field(default=None, description="Faculty / Department")
    specialization: str | None = Field(default=None, description="Specialization")
    cpa: str | None = Field(default=None, description="CPA / GPA")
    degree_number: str | None = Field(default=None, description="Degree number")
    register_number: str | None = Field(default=None, description="Book register number")
    notes: str | None = Field(default=None, description="Notes")
    phone: str | None = Field(default=None, description="Phone number")
    status: str = Field(
        ...,
        description="Credential status ('claimed', 'unclaimed', or 'revoked')",
    )
    claim_method: str | None = Field(default=None, description="Claim method")
    claimed_at: str | None = Field(default=None, description="Claimed timestamp in ISO format")
    unclaimed_at: str | None = Field(
        default=None,
        description="Unclaimed timestamp in ISO format",
    )
    revoked_reason: str | None = Field(default=None, description="Revocation reason")
    revoked_at: str | None = Field(
        default=None,
        description="Revoked timestamp in ISO format",
    )
    created_at: str | None = Field(default=None, description="Created timestamp in ISO format")
    restored_at: str | None = Field(
        default=None,
        description="Restored timestamp in ISO format",
    )


__all__ = [
    "IssuerRegistrationData",
    "IssuerRegistrationRequest",
    "PasswordSubmitRequest",
    "OtpVerifyRequest",
    "GenericApiResponse",
    "CredentialImportData",
    "ExistingCredentialData",
    "IncomingCredentialData",
    "DuplicateCredentialItemData",
    "CheckDuplicatesData",
    "ManualCredentialCreateRequest",
    "ManualCredentialResponseData",
    "CredentialSummaryData",
    "CredentialListItemData",
    "CredentialPaginationData",
    "IssuerCredentialListData",
    "IssuerCredentialDetailData",
]




