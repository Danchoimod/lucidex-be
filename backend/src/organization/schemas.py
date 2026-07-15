"""Organization request and response DTOs."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from src.organization.models import OrganizationStatus
from src.utils.check_format import (
    normalize_email,
    normalize_phone,
    normalize_tax_code,
    validate_gmail_format,
    validate_phone_format,
    validate_tax_code_format,
)


class IssuerRegistrationRequest(BaseModel):
    """Public form used by an institution to apply as an issuer."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=200)
    tax_code: str
    address: str = Field(min_length=1, max_length=500)
    legal_rep_name: str = Field(min_length=1, max_length=200)
    contact_email: EmailStr
    contact_phone: str
    registrant_name: str = Field(min_length=1, max_length=200)

    @field_validator("tax_code", mode="before")
    @classmethod
    def normalize_and_validate_tax_code(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("Tax code must be a string.")
        normalized = normalize_tax_code(value)
        if not validate_tax_code_format(normalized):
            raise ValueError("Invalid tax code format.")
        return normalized

    @field_validator("contact_email", mode="before")
    @classmethod
    def normalize_and_validate_contact_email(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("Contact email must be a string.")
        normalized = normalize_email(value)
        if not validate_gmail_format(normalized):
            raise ValueError("Contact email must be a valid Gmail address.")
        return normalized

    @field_validator("contact_phone", mode="before")
    @classmethod
    def normalize_and_validate_contact_phone(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("Contact phone must be a string.")
        normalized = normalize_phone(value)
        if not validate_phone_format(normalized):
            raise ValueError("Invalid phone number format.")
        return normalized


class IssuerRegistrationData(BaseModel):
    id: str
    status: OrganizationStatus
