"""Issuer schemas entry point."""

from pydantic import BaseModel, Field

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
    storage_path: str = Field(..., description="Storage path or public URL of uploaded CSV file")


__all__ = [
    "IssuerRegistrationData",
    "IssuerRegistrationRequest",
    "PasswordSubmitRequest",
    "OtpVerifyRequest",
    "GenericApiResponse",
    "CredentialImportData",
]
