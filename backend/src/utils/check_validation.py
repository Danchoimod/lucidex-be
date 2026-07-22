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
    organization_type: Literal["issuer", "verifier"] | str,
) -> bool:
    """Check whether the tax code is unused by a live organization of the specified type."""
    tax_code = normalize_tax_code(tax_code)
    org_type_val = getattr(organization_type, "value", organization_type)
    existing_organization = await Organization.find_one(
        Organization.tax_code == tax_code,
        Organization.type == org_type_val,
        {"status": {"$in": list(LIVE_ORGANIZATION_STATUSES)}},
    )

    return existing_organization is None


from src.organization.models import LIVE_ORGANIZATION_STATUSES, Organization
from src.owner.models import Owner


async def is_contact_email_available(email: str) -> bool:
    """Check whether the email is unused by any live organization (issuer/verifier) or owner."""
    email = normalize_email(email)
    existing_organization = await Organization.find_one(
        Organization.contact_email == email,
        {"status": {"$in": list(LIVE_ORGANIZATION_STATUSES)}},
    )
    if existing_organization is not None:
        return False

    existing_owner = await Owner.find_one(Owner.email == email)
    return existing_owner is None


async def is_contact_phone_available(phone: str) -> bool:
    """Check whether the phone number is unused by any live organization (issuer/verifier) or owner."""
    phone = normalize_phone(phone)
    existing_organization = await Organization.find_one(
        Organization.contact_phone == phone,
        {"status": {"$in": list(LIVE_ORGANIZATION_STATUSES)}},
    )
    if existing_organization is not None:
        return False

    existing_owner = await Owner.find_one(Owner.phone == phone)
    return existing_owner is None


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

    if not await is_contact_email_available(contact_email, "issuer"):
        raise ValueError("Contact email is already registered.")

    if not await is_contact_phone_available(contact_phone, "issuer"):
        raise ValueError("Contact phone number is already registered.")
