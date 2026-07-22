from typing import Any, Literal

from src.organization.models import LIVE_ORGANIZATION_STATUSES
from src.organization.models import Organization
from src.utils.check_format import (
    normalize_email,
    normalize_phone,
    normalize_tax_code,
    validate_gmail_format,
    validate_phone_format,
    validate_tax_code_format,
)


def read_required_string(data: Any, field_name: str) -> str:
    """Read a required string field from a dict or object."""
    if isinstance(data, dict):
        value = data.get(field_name)
    else:
        value = getattr(data, field_name, None)

    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} is required.")

    return value.strip()


async def is_tax_code_available(
    tax_code: str,
    organization_type: Literal["issuer", "verifier"],
) -> bool:
    """Check whether the tax code is unused by a live organization."""
    tax_code = normalize_tax_code(tax_code)
    existing_organization = await Organization.find_one(
        Organization.tax_code == tax_code,
        Organization.type == organization_type,
        {"status": {"$in": list(LIVE_ORGANIZATION_STATUSES)}},
    )

    return existing_organization is None


async def is_contact_email_available(email: str) -> bool:
    """Check whether the email is unused by live organizations."""
    email = normalize_email(email)
    existing_organization = await Organization.find_one(
        Organization.contact_email == email,
        {"status": {"$in": list(LIVE_ORGANIZATION_STATUSES)}},
    )

    return existing_organization is None


async def validate_issuer_registration_data(data: Any) -> None:
    """Validate issuer registration fields and business rules."""

    tax_code = normalize_tax_code(
        read_required_string(data, "tax_code")
    )

    contact_email = normalize_email(
        read_required_string(data, "contact_email")
    )

    contact_phone = normalize_phone(
        read_required_string(data, "contact_phone")
    )

    if not validate_tax_code_format(tax_code):
        raise ValueError("Invalid tax code format.")

    if not validate_gmail_format(contact_email):
        raise ValueError(
            "Contact email must be a valid email address."
        )

    if not validate_phone_format(contact_phone):
        raise ValueError("Invalid phone number format.")

    if not await is_tax_code_available(tax_code, "issuer"):
        raise ValueError("Tax code is already registered.")

    if not await is_contact_email_available(contact_email):
        raise ValueError("Contact email is already registered.")
