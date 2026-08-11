"""Dependencies for the issuer module."""

from typing import Annotated

from fastapi import Depends

from src.auth.dependencies import require_current_actor
from src.issuer.exceptions import IssuerForbiddenError
from src.organization.constants import OrganizationType
from src.organization.models import InstitutionAccount, Organization


async def require_current_issuer(
    actor_info: Annotated[tuple, Depends(require_current_actor)],
) -> tuple[InstitutionAccount, Organization]:
    """Dependency that ensures the current authenticated user is an active Issuer institution account.

    Returns:
        tuple[InstitutionAccount, Organization]: The institution account and its parent organization.
    """
    account, session, actor_type = actor_info

    if actor_type != "institution_account" or not isinstance(account, InstitutionAccount):
        raise IssuerForbiddenError("Issuer permission required.")

    organization = await Organization.get(account.org_id)
    if organization is None:
        raise IssuerForbiddenError("Associated organization not found.")

    # Compare organization type (enum or string value)
    org_type_str = (
        organization.type.value
        if isinstance(organization.type, OrganizationType)
        else str(organization.type)
    )

    if org_type_str != OrganizationType.ISSUER.value:
        raise IssuerForbiddenError("Only Issuer organizations can access this resource.")

    return account, organization
